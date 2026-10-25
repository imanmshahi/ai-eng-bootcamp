"""Code-based eval checks for /ask traces — no LLM calls, no network, no API key.

Every check takes one trace dict and returns (passed: bool, reason: str).  `passed=True` means
the check found nothing wrong; `reason` always explains the verdict, so a passing run is as
readable as a failing one.

A check can only test what is decidable from the trace itself.  None of these knows the right
answer, so none of them can tell you an answer is *wrong* — they catch self-contradictions
(cited something that was never retrieved, refused while citing) and shapes that are suspicious
on their face (a percentage with no citation).  Categories C1, C4 and C5 in evals/TAXONOMY.md
need a gold label and are deliberately out of scope here.

Trace shape (see evals/traces_v1.jsonl):
    {"id", "question", "answer", "citations": [str], "refused": bool,
     "tokens_used": int, "retrieved": [{"chunk_id", "document_id", "score"}]}
"""

from __future__ import annotations

import re
from typing import Any

Trace = dict[str, Any]
Result = tuple[bool, str]

# A chunk ID as the API mints it: f"{document_id}#{index:04d}" (server/rag.py chunk_id()).
# document_id is author-chosen, so allow letters, digits, dot, underscore and hyphen.
_CHUNK_ID_IN_PROSE = re.compile(r"\[([A-Za-z0-9._-]+#\d+)\]")

# A percentage in either decimal convention: the corpus writes "35,6 %" (EU), the model
# usually answers "35.6%".  Also catches a bare "29%".
_PERCENTAGE = re.compile(r"\d+(?:[.,]\d+)?\s*%")

# A decimal number used as a rate without a % sign, e.g. "a rate of 21,7".  Plain integers are
# excluded on purpose: years (2030) and article numbers (27) would otherwise fire constantly.
_DECIMAL_RATE = re.compile(r"\b\d+[.,]\d+\b")

# Hedges that concede a gap while still answering — the C2 shape.  The fixed refusal sentence is
# deliberately NOT in this list; see the note in check_declined_despite_retrieval.
# Hedges, matched by shape rather than by a fixed phrase list.
#
# A literal list was the first version and it broke the one job it had. Between two runs the
# model reworded "not detailed in the provided context" to "not fully described in the provided
# context"; the concession was identical, the list missed it, and the check silently reported an
# improvement that had not happened. Recall that depends on the model's choice of adverb is not
# recall. So: match the *pattern* — a negated verb of stating/covering, with an optional adverb.
#
# Two parts, both anchored on that structure:
#   1. "not [adverb] <stated/specified/detailed/described/covered/…>"
#   2. "does not <specify/provide/mention/…>" / "cannot (fully) answer" / "no specific"
_HEDGE_VERBS = (
    "detailed|explicitly|specified|specify|provided|stated|mentioned|described|covered|"
    "included|available|clear|given|listed|defined|indicated"
)
_HEDGE = re.compile(
    r"\bnot\s+(?:\w+ly\s+)?(?:" + _HEDGE_VERBS + r")\b"
    r"|\bdoes\s+not\s+(?:\w+ly\s+)?(?:specify|provide|mention|state|detail|describe|include|"
    r"cover|list|define|indicate)\b"
    r"|\bcan(?:not|'t)\s+(?:\w+ly\s+)?answer\b"
    r"|\bno\s+specific\b"
    r"|\b(?:un|not\s+)clear\s+from\b"
)


def hedges_in(answer: str) -> list[str]:
    """The hedge concessions in an answer, as matched text. Empty when it concedes nothing."""
    seen: list[str] = []
    for m in _HEDGE.finditer(_normalise(answer)):
        phrase = m.group(0)
        if phrase not in seen:
            seen.append(phrase)
    return seen

# "5 chunks were retrieved" — the live k for /ask.  At this many chunks a decline is suspicious
# because the model had the full context budget to work with.
MIN_RETRIEVED_FOR_HEDGE_FLAG = 5


def _retrieved_ids(trace: Trace) -> list[str]:
    return [r.get("chunk_id", "") for r in trace.get("retrieved") or []]


def _normalise(text: str) -> str:
    """Collapse whitespace and straighten curly apostrophes — the model mixes ' and ' (see F2)."""
    return " ".join((text or "").replace("’", "'").split()).lower()


def ids_in_prose(answer: str) -> list[str]:
    """Bracketed chunk IDs in the answer text, in order, de-duplicated."""
    seen: list[str] = []
    for match in _CHUNK_ID_IN_PROSE.findall(answer or ""):
        if match not in seen:
            seen.append(match)
    return seen


# ── Check 1 — targets C3 citation-mismatch ────────────────────────────
def check_citations_were_retrieved(trace: Trace) -> Result:
    """Every chunk ID in the answer prose and in `citations` must appear in `retrieved`.

    Checks the prose as well as the field because F3 showed the two can disagree: the
    structured `citations` was clean while the text the user reads carried an invented ID.
    """
    retrieved = set(_retrieved_ids(trace))
    prose_ids = ids_in_prose(trace.get("answer", ""))
    cited_ids = list(trace.get("citations") or [])

    bad_prose = [i for i in prose_ids if i not in retrieved]
    bad_cited = [i for i in cited_ids if i not in retrieved]

    if bad_prose or bad_cited:
        parts = []
        if bad_prose:
            parts.append(f"in answer prose but never retrieved: {', '.join(sorted(bad_prose))}")
        if bad_cited:
            parts.append(f"in citations but never retrieved: {', '.join(sorted(bad_cited))}")
        return False, "; ".join(parts)

    counted = len(set(prose_ids) | set(cited_ids))
    if counted == 0:
        return True, "no chunk IDs cited, nothing to verify"
    return True, f"all {counted} cited ID(s) were retrieved"


# ── Check 2 — targets the F2 class (refusal / citation contradiction) ─
def check_refusal_consistency(trace: Trace) -> Result:
    """`refused=True` requires empty citations; `refused=False` requires at least one.

    Either contradiction is a defect regardless of the answer's content: a refusal that cites
    sources is incoherent, and a non-refusal with no sources is the ungrounded-but-confident
    state that F2 produced.
    """
    refused = bool(trace.get("refused"))
    citations = list(trace.get("citations") or [])

    if refused and citations:
        return False, f"refused=True but cites {len(citations)}: {', '.join(citations)}"
    if not refused and not citations:
        return False, "refused=False but citations is empty — answered with no grounding"
    if refused:
        return True, "refused=True with no citations"
    return True, f"refused=False with {len(citations)} citation(s)"


# ── Check 3 — targets C2 under-synthesis (uncited numbers) ────────────
def check_no_uncited_numbers(trace: Trace) -> Result:
    """If the answer states a percentage or a decimal rate, at least one citation must be present.

    A bare number is the highest-stakes thing /ask emits — a duty rate or a mandate share — and
    is exactly what a reader needs to be able to check.  Refused traces carry no numbers, so
    they pass without a special case.
    """
    answer = trace.get("answer", "") or ""
    citations = list(trace.get("citations") or [])

    percentages = _PERCENTAGE.findall(answer)
    # Don't double-count a decimal that is already part of a matched percentage.
    pct_span_text = " ".join(percentages)
    decimals = [d for d in _DECIMAL_RATE.findall(answer) if d not in pct_span_text]
    numbers = percentages + decimals

    if not numbers:
        return True, "no percentage or decimal rate in the answer"
    if not citations:
        shown = ", ".join(numbers[:5]) + ("…" if len(numbers) > 5 else "")
        return False, f"states {len(numbers)} number(s) ({shown}) with no citation"
    return True, f"{len(numbers)} number(s) stated, {len(citations)} citation(s) present"


# ── Check 4 — targets C2 under-synthesis (hedged decline) ─────────────
def check_declined_despite_retrieval(trace: Trace) -> Result:
    """Flag a hedge phrase in the answer when the full k=5 chunks were retrieved.

    The model conceding "not specified in the provided context" after being handed five chunks
    means either the retrieval was off-target (C1) or it under-used what it had (C2).  The check
    cannot tell which, so treat a failure as a triage flag, not a verdict.

    Scope note: the *fixed refusal sentence* is not treated as a hedge.  Including it would catch
    q11 — which refused with 5 chunks while the answer sat in the rank-1 chunk — but would also
    flag q16/q17/q18, where refusing was correct because the fact is absent from the corpus.
    Separating those needs a per-question answerability label, which this check does not have.
    See the coverage section of evals/TAXONOMY.md.
    """
    answer = _normalise(trace.get("answer", ""))
    n_retrieved = len(_retrieved_ids(trace))

    found = hedges_in(answer)
    if not found:
        return True, f"no hedge phrase ({n_retrieved} chunk(s) retrieved)"
    if n_retrieved < MIN_RETRIEVED_FOR_HEDGE_FLAG:
        return (
            True,
            f"hedge present ({', '.join(found)}) but only {n_retrieved} chunk(s) retrieved "
            f"— below the {MIN_RETRIEVED_FOR_HEDGE_FLAG}-chunk flag threshold",
        )
    return False, f"hedged ({', '.join(found)}) despite {n_retrieved} chunks retrieved"


# ── Check 5 — targets C2 under-synthesis, using the human label ───────
# The fixed refusal sentence, as server/openai_client.py emits it.
REFUSAL_SENTENCE = "I don't have enough information in the provided documents to answer that."


def declined(trace: Trace) -> tuple[bool, str]:
    """Did this trace decline to answer, by any route? (declined, how)

    Three routes, because the pipeline has three ways of giving up: the `refused` flag, the fixed
    refusal sentence anywhere in the prose (F2's hedge-then-refuse shape), and a hedge phrase.
    """
    answer = _normalise(trace.get("answer", ""))
    if _normalise(REFUSAL_SENTENCE) in answer:
        return True, "returned the fixed refusal sentence"
    if bool(trace.get("refused")):
        return True, "refused=True"
    found = hedges_in(answer)
    if found:
        return True, f"hedged ({', '.join(found)})"
    return False, "answered"


def check_over_refusal(trace: Trace) -> Result:
    """Fail when the human labelled the question answerable=Yes and the model declined anyway.

    Needs `trace["answerable"]`, which run_evals.py merges in from evals/labels_v1.jsonl.  This
    is the one check with access to a human judgement, which is what lets it see the failures the
    other four cannot: q11 declined with the fixed refusal sentence while the answer sat in its
    rank-1 chunk, and no amount of regex over the trace alone can tell that from a correct
    refusal like q16.

    Unlabelled traces pass with a reason saying so — they are *not evaluated*, and
    over_refusal_rate() excludes them from both halves of the fraction rather than counting them
    as successes.  Answerable=Partly also passes: a partial decline there may be correct, and
    scoring it needs to know which part was declined.
    """
    answerable = (trace.get("answerable") or "").strip()
    gave_up, how = declined(trace)

    if not answerable:
        return True, "not evaluated — no answerable label for this question"
    if answerable == "No":
        return True, f"answerable=No, {how} — declining is correct here"
    if answerable == "Partly":
        return True, f"answerable=Partly, {how} — not scored (see docstring)"
    if answerable != "Yes":
        return True, f"unrecognised answerable value {answerable!r} — not evaluated"
    if gave_up:
        n = len(_retrieved_ids(trace))
        return False, f"answerable=Yes but {how} ({n} chunk(s) retrieved) — over-refusal"
    return True, "answerable=Yes and answered"


def over_refusal_rate(traces: list[Trace]) -> dict[str, Any]:
    """wrongly-refused / answerable, over the traces labelled answerable=Yes.

    Returns the parts as well as the rate so a report can show the fraction, and `rate: None`
    when nothing is labelled yet — an unlabelled run has no over-refusal rate, which is a
    different statement from a rate of 0.0.
    """
    yes = [t for t in traces if (t.get("answerable") or "").strip() == "Yes"]
    wrongly = [t for t in yes if declined(t)[0]]
    labelled = [t for t in traces if (t.get("answerable") or "").strip()]
    return {
        "answerable_yes": len(yes),
        "wrongly_refused": len(wrongly),
        "wrongly_refused_ids": [t.get("id", "?") for t in wrongly],
        "rate": (len(wrongly) / len(yes)) if yes else None,
        "traces_labelled": len(labelled),
        "traces_unlabelled": len(traces) - len(labelled),
    }


# Registry — run_evals.py iterates this, so adding a check here is enough to include it.
CHECKS = {
    "citations_were_retrieved": check_citations_were_retrieved,
    "refusal_consistency": check_refusal_consistency,
    "no_uncited_numbers": check_no_uncited_numbers,
    "declined_despite_retrieval": check_declined_despite_retrieval,
    "over_refusal": check_over_refusal,
}

# What each check is aimed at, for the report header.
TARGETS = {
    "citations_were_retrieved": "C3 citation-mismatch",
    "refusal_consistency": "F2 class (refusal/citation contradiction)",
    "no_uncited_numbers": "C2 under-synthesis",
    "declined_despite_retrieval": "C2 under-synthesis",
    "over_refusal": "C2 under-synthesis (needs answerable label)",
}


def run_all(trace: Trace) -> dict[str, Result]:
    """Every check against one trace, keyed by check name."""
    return {name: fn(trace) for name, fn in CHECKS.items()}
