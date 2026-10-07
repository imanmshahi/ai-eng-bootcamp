"""OpenAI call for POST /ask and optional prompt complexity classification."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from server.rag import search as rag_search
from server.schemas import AskResponse, SearchRequest

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"
CLASSIFIER_MAX_INPUT_CHARS = 4_000
_classification_cache: dict[str, dict[str, Any]] = {}

# gpt-4o-mini rough catalog rates ($ / 1M tokens) for local spend guard only
_INPUT_PER_M = 0.15
_OUTPUT_PER_M = 0.60
_HARD_MAX_TOKENS = 500
_CLASSIFIER_HARD_MAX_TOKENS = 300
_CLASSIFIER_PER_CALL_MAX_USD = 0.02
_CLASSIFIER_APPROVAL_PREDICTED_USD = 0.05
_CLASSIFIER_APPROVAL_REMAINING_USD = 0.10

_spend_day: date | None = None
_spend_usd: float = 0.0

_classifier_spend_day: date | None = None
_classifier_spend_usd: float = 0.0


def _api_key_available() -> bool:
    api_key = os.getenv("OPENAI_API_KEY")
    return bool(api_key and not api_key.startswith("sk-your-key"))


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _ask_max_tokens() -> int:
    raw = int(os.getenv("ASK_MAX_TOKENS", "300"))
    return max(1, min(raw, _HARD_MAX_TOKENS))


def _ask_max_usd() -> float:
    return float(os.getenv("ASK_MAX_USD", "1.0"))


def _classifier_max_tokens() -> int:
    raw = int(os.getenv("CLASSIFIER_MAX_TOKENS", "300"))
    return max(1, min(raw, _CLASSIFIER_HARD_MAX_TOKENS))


def _classifier_max_usd() -> float:
    """Separate daily wallet from /ask. CLASSIFIER_MAX_USD preferred; ANALYZE_MAX_USD alias."""
    raw = os.getenv("CLASSIFIER_MAX_USD")
    if raw is None or raw.strip() == "":
        raw = os.getenv("ANALYZE_MAX_USD", "0.50")
    return float(raw)


def _env_spend_approved() -> bool:
    return os.getenv("CLASSIFIER_SPEND_APPROVED", "").strip().lower() in ("1", "true", "yes")


def _reset_daily_if_needed() -> None:
    global _spend_day, _spend_usd
    today = date.today()
    if _spend_day != today:
        _spend_day = today
        _spend_usd = 0.0


def _reset_classifier_daily_if_needed() -> None:
    global _classifier_spend_day, _classifier_spend_usd
    today = date.today()
    if _classifier_spend_day != today:
        _classifier_spend_day = today
        _classifier_spend_usd = 0.0


def _estimate_call_usd(text: str, max_tokens: int) -> float:
    input_tokens = max(1, len(text) // 4 + 40)
    return (input_tokens * _INPUT_PER_M + max_tokens * _OUTPUT_PER_M) / 1_000_000


def _usage_usd(usage: Any, predicted: float) -> float:
    if usage is not None:
        return (usage.prompt_tokens * _INPUT_PER_M + usage.completion_tokens * _OUTPUT_PER_M) / 1_000_000
    return predicted


_REFUSAL = "I don't have enough information in the provided documents to answer that."

_RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question ONLY from the context "
    "below. Cite every chunk you use by its ID in square brackets, like [notes.md#0002]. "
    "If the answer is not in the context, reply exactly:\n"
    f'"{_REFUSAL}"'
)


def _build_context_block(hits: list[dict]) -> str:
    """Format retrieved chunks so the LLM sees [chunk_id] before each text."""
    parts = []
    for hit in hits:
        parts.append(f"[{hit['chunk_id']}]\n{hit['text']}")
    return "\n\n".join(parts)


def _extract_citations(answer: str, retrieved_ids: set[str]) -> list[str]:
    """Pull every [bracketed] token from the answer, keep only IDs that were actually retrieved."""
    raw = re.findall(r"\[([^\]]+)\]", answer)
    # Deduplicate while preserving order
    seen: set[str] = set()
    valid: list[str] = []
    for cid in raw:
        if cid in retrieved_ids and cid not in seen:
            seen.add(cid)
            valid.append(cid)
    return valid


def ask_openai(question: str) -> AskResponse:
    global _spend_usd

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-your-key"):
        raise ValueError("OPENAI_API_KEY is missing. Copy .env.example to .env and add your key.")

    # ── Step 1: Retrieve top-k chunks ─────────────────────────────────
    search_result = rag_search(SearchRequest(question=question, k=3))
    search_cost = search_result.cost_usd
    search_tokens = search_result.tokens_used

    # If nothing has been ingested, refuse immediately — no LLM call needed.
    if not search_result.results:
        return AskResponse(
            answer=_REFUSAL,
            confidence=0.0,
            tokens_used=search_tokens,
            cost_usd=search_cost,
            citations=[],
            refused=True,
        )

    # ── Step 2: Build context block ───────────────────────────────────
    hits = [h.model_dump() for h in search_result.results]
    context_block = _build_context_block(hits)
    retrieved_ids = {h["chunk_id"] for h in hits}

    # ── Step 3: LLM call with RAG system prompt ───────────────────────
    max_tokens = _ask_max_tokens()
    ask_max_usd = _ask_max_usd()
    _reset_daily_if_needed()
    user_message = f"Context:\n{context_block}\n\nQuestion: {question}"
    predicted = _estimate_call_usd(user_message, max_tokens)
    if _spend_usd + predicted > ask_max_usd:
        raise ValueError(
            f"ASK daily spend guard reached (ASK_MAX_USD={ask_max_usd}). "
            "Raise ASK_MAX_USD in .env or wait until tomorrow. "
            "Platform OpenAI billing limits are separate (dashboard)."
        )

    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": _RAG_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=max_tokens,
    )

    actual = _usage_usd(completion.usage, predicted)
    _spend_usd += actual

    usage = completion.usage
    if usage is not None:
        tokens_used = usage.total_tokens
    else:
        tokens_used = max(1, len(user_message) // 4 + 40) + max_tokens

    # ── Step 4: Extract citations and detect refusal ──────────────────
    answer = (completion.choices[0].message.content or "").strip()
    refused = answer == _REFUSAL
    citations = _extract_citations(answer, retrieved_ids)

    total_cost = search_cost + actual
    total_tokens = search_tokens + tokens_used

    return AskResponse(
        answer=answer,
        confidence=0.0 if refused else 0.85,
        tokens_used=total_tokens,
        cost_usd=total_cost,
        citations=citations,
        refused=refused,
    )


def _assert_classifier_spend_allowed(prompt_text: str, *, spend_approved: bool) -> tuple[int, float]:
    """Fail-closed classifier guards. Returns (max_tokens, predicted_usd)."""
    max_tokens = _classifier_max_tokens()
    daily_max = _classifier_max_usd()
    _reset_classifier_daily_if_needed()
    predicted = _estimate_call_usd(prompt_text, max_tokens)

    if predicted > _CLASSIFIER_PER_CALL_MAX_USD:
        raise ValueError(
            f"Classifier per-call spend guard exceeded "
            f"(predicted ${predicted:.4f} > ${_CLASSIFIER_PER_CALL_MAX_USD:.2f}). "
            "Shorten the prompt or lower CLASSIFIER_MAX_TOKENS."
        )

    remaining = daily_max - _classifier_spend_usd
    if _classifier_spend_usd + predicted > daily_max:
        raise ValueError(
            f"Classifier daily spend guard reached "
            f"(CLASSIFIER_MAX_USD/ANALYZE_MAX_USD={daily_max}). "
            "Raise CLASSIFIER_MAX_USD in .env or wait until tomorrow. "
            "This wallet is separate from ASK_MAX_USD (/ask)."
        )

    needs_approval = (
        predicted > _CLASSIFIER_APPROVAL_PREDICTED_USD
        or remaining < _CLASSIFIER_APPROVAL_REMAINING_USD
    )
    approved = spend_approved or _env_spend_approved()
    if needs_approval and not approved:
        raise ValueError(
            "Classifier spend approval required "
            f"(predicted ${predicted:.4f} or daily remaining ${remaining:.4f} < "
            f"${_CLASSIFIER_APPROVAL_REMAINING_USD:.2f}). "
            "Set classifier_spend_approved=true on the request, check the Streamlit "
            "approval box, or set CLASSIFIER_SPEND_APPROVED=1 in .env."
        )

    return max_tokens, predicted


def classify_prompt_complexity(
    prompt_text: str,
    *,
    spend_approved: bool = False,
) -> dict[str, Any] | None:
    """LLM classifier for prompt complexity. Returns None if no API key."""
    global _classifier_spend_usd

    if not _api_key_available():
        return None

    trimmed = prompt_text.strip()[:CLASSIFIER_MAX_INPUT_CHARS]
    key = _cache_key(trimmed)
    if key in _classification_cache:
        return _classification_cache[key]

    max_tokens, predicted = _assert_classifier_spend_allowed(trimmed, spend_approved=spend_approved)

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    completion = client.chat.completions.create(
        model=DEFAULT_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify prompt complexity for cost forecasting. "
                    "Return JSON with integer fields 1-5: input_size, output_depth, "
                    "reasoning_depth, verification_need, ambiguity_risk, agentic_pattern; "
                    "primary_steps (1-5), checker_steps (0-3); "
                    'result_shape one of "short", "paragraph", "report"; '
                    "confidence (0.0-1.0)."
                ),
            },
            {"role": "user", "content": trimmed},
        ],
        max_tokens=max_tokens,
        temperature=0,
    )

    actual = _usage_usd(completion.usage, predicted)
    if actual > _CLASSIFIER_PER_CALL_MAX_USD:
        # Still record spend, but fail closed so callers do not treat as success quietly.
        _classifier_spend_usd += actual
        raise ValueError(
            f"Classifier per-call actual spend exceeded "
            f"(${actual:.4f} > ${_CLASSIFIER_PER_CALL_MAX_USD:.2f})."
        )
    _classifier_spend_usd += actual

    raw = completion.choices[0].message.content or "{}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        payload = json.loads(match.group(0)) if match else {}

    _classification_cache[key] = payload
    return payload
