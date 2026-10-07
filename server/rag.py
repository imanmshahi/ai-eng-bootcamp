"""RAG ingest for POST /ingest — chunk text, embed with OpenAI, keep vectors in memory.

The store lives in process memory: it resets on restart / redeploy (Render free tier
has no persistent disk anyway). Swap _store for Chroma when you need persistence.
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

import math

from server.schemas import IngestRequest, IngestResponse, SearchRequest, SearchResponse

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
# text-embedding-3-small rate ($ / 1M tokens) for the local spend guard + cost readout
_EMBED_PER_M = 0.02

# chunk_id -> {"id", "document_id", "chunk_index", "text", "embedding"}
_store: dict[str, dict[str, Any]] = {}

_spend_day: date | None = None
_spend_usd: float = 0.0


def _ingest_max_usd() -> float:
    return float(os.getenv("INGEST_MAX_USD", "0.10"))


def _reset_daily_if_needed() -> None:
    global _spend_day, _spend_usd
    today = date.today()
    if _spend_day != today:
        _spend_day = today
        _spend_usd = 0.0


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Fixed-size character windows; each window starts chunk_size - chunk_overlap after the last."""
    step = chunk_size - chunk_overlap
    chunks = []
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(text):
            break
    return chunks


def chunk_id(document_id: str, index: int) -> str:
    """Readable, deterministic ID: same document + position always gives the same ID."""
    return f"{document_id}#{index:04d}"


def _delete_document(document_id: str) -> int:
    stale = [cid for cid, row in _store.items() if row["document_id"] == document_id]
    for cid in stale:
        del _store[cid]
    return len(stale)


def ingest(body: IngestRequest) -> IngestResponse:
    """Chunk, embed, and upsert a document into the in-memory store.

    Empty or whitespace-only text is a **no-op**: the call returns 0 chunks_added
    without touching existing chunks for this document_id.  To remove a document,
    use a future DELETE endpoint (not yet built).
    """
    global _spend_usd

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-your-key"):
        raise ValueError("OPENAI_API_KEY is missing. Copy .env.example to .env and add your key.")

    chunks = chunk_text(body.text, body.chunk_size, body.chunk_overlap)
    if not chunks:
        return IngestResponse(
            document_id=body.document_id,
            chunks_added=0,
            chunks_replaced=0,
            total_chunks=len(_store),
            tokens_used=0,
            cost_usd=0.0,
        )

    ingest_max_usd = _ingest_max_usd()
    _reset_daily_if_needed()
    predicted = sum(len(chunk) // 4 + 1 for chunk in chunks) * _EMBED_PER_M / 1_000_000
    if _spend_usd + predicted > ingest_max_usd:
        raise ValueError(
            f"INGEST daily spend guard reached (INGEST_MAX_USD={ingest_max_usd}). "
            "Raise INGEST_MAX_USD in .env or wait until tomorrow."
        )

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=chunks)

    tokens_used = response.usage.total_tokens
    cost_usd = tokens_used * _EMBED_PER_M / 1_000_000
    _spend_usd += cost_usd

    # Build replacement rows first so the delete→insert pair is atomic from the
    # caller's view: if row construction fails, the old document stays intact.
    new_rows = {}
    for i, (chunk, item) in enumerate(zip(chunks, sorted(response.data, key=lambda d: d.index))):
        cid = chunk_id(body.document_id, i)
        new_rows[cid] = {
            "id": cid,
            "document_id": body.document_id,
            "chunk_index": i,
            "text": chunk,
            "embedding": item.embedding,
        }
    chunks_replaced = _delete_document(body.document_id)
    _store.update(new_rows)

    return IngestResponse(
        document_id=body.document_id,
        chunks_added=len(chunks),
        chunks_replaced=chunks_replaced,
        total_chunks=len(_store),
        tokens_used=tokens_used,
        cost_usd=cost_usd,
    )


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors, no numpy needed.

    dot  = Σ aᵢbᵢ           — how much the vectors point in the same direction.
    norm = √(Σ xᵢ²)         — length of each vector.
    cos  = dot / (‖a‖ · ‖b‖) — 1.0 when identical, 0.0 when orthogonal.
    """
    dot = sum(ai * bi for ai, bi in zip(a, b))        # numerator
    norm_a = math.sqrt(sum(ai * ai for ai in a))       # length of a
    norm_b = math.sqrt(sum(bi * bi for bi in b))       # length of b
    if norm_a == 0.0 or norm_b == 0.0:                 # zero vector → no direction
        return 0.0
    return dot / (norm_a * norm_b)


def search(body: SearchRequest) -> SearchResponse:
    """Embed the question once, score every stored chunk, return top-k.

    Pure vector retrieval — no LLM generation, no chat call.
    """
    global _spend_usd

    # --- guard: need an API key to embed the question ---
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-your-key"):
        raise ValueError("OPENAI_API_KEY is missing. Copy .env.example to .env and add your key.")

    # --- guard: nothing to search ---
    if not _store:
        return SearchResponse(results=[], tokens_used=0, cost_usd=0.0)

    # --- embed the question (single string → one embedding) ---
    _reset_daily_if_needed()
    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[body.question])

    tokens_used = response.usage.total_tokens
    cost_usd = tokens_used * _EMBED_PER_M / 1_000_000
    _spend_usd += cost_usd

    q_vec = response.data[0].embedding  # the question's embedding vector

    # --- score every chunk against the question vector ---
    scored = [
        (cid, row, _cosine_similarity(q_vec, row["embedding"]))
        for cid, row in _store.items()
    ]

    # --- sort descending by score, keep the top k ---
    scored.sort(key=lambda t: t[2], reverse=True)
    top_k = scored[: body.k]

    # --- build the response list ---
    results = [
        {
            "chunk_id": cid,
            "document_id": row["document_id"],
            "score": round(score, 6),    # 6 decimals is plenty for display
            "text": row["text"],
        }
        for cid, row, score in top_k
    ]

    return SearchResponse(results=results, tokens_used=tokens_used, cost_usd=cost_usd)
