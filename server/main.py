"""Week 1 server — /health, POST /ask, POST /estimate."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException

from server.analyze_service import run_analyze
from server.estimate_service import run_estimate
from server.openai_client import ask_openai
from server.memory import (
    backend as memory_backend,
    init_store,
    probe as memory_probe,
    story_count,
    warn_if_unconfigured,
)
from server.rag import ingest as run_ingest, search as run_search, store_chunk_count
from server.watchbird_classify import screen as run_screen
from server.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AskRequest,
    AskResponse,
    EstimateRequest,
    EstimateResponse,
    IngestRequest,
    IngestResponse,
    PingRequest,
    PingResponse,
    SearchRequest,
    SearchResponse,
)

logger = logging.getLogger("bootcamp")

# When this process started. Set at import, so it is the process's own clock rather than
# anything the platform reports.
#
# Why /health needs it: a restart that changes no code returns a byte-identical /health body, so
# "the container restarted" is otherwise an assertion with nothing behind it. started_at makes it
# a reading — a new container has a new value and uptime_seconds near zero, while
# stories_remembered carries over, which is the whole claim the Postgres store exists to support.
#
# This is a partial fix for the durable gap named in F11: identifying *which process answered*.
# The complete version is a build identifier, and Render injects one as RENDER_GIT_COMMIT, but
# reporting it would mean printing an environment variable value, which CLAUDE.md rule 1 forbids
# without exception. That rule is about secrets and a commit SHA is not one, so the carve-out may
# be worth making - but it is a change to an absolute rule, and that is Iman's call, not mine.
_STARTED_AT = datetime.now(timezone.utc)

# Uvicorn configures only its own loggers, so our records would propagate to a
# root logger that defaults to WARNING and drop the ingest lines below.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")

# ---------------------------------------------------------------------------
# Startup: auto-load corpus/ into the RAG store
# ---------------------------------------------------------------------------

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"

# Attempts per file before giving up. Embedding calls time out transiently (F6), and a single
# timeout used to cost the whole document for the lifetime of the process.
CORPUS_LOAD_ATTEMPTS = 3

# Startup result, read by /health so an incomplete store cannot report itself as healthy.
# chunks_total is read back from the store rather than from the last ingest response, which
# went stale whenever the final file was the one that failed.
_corpus_status: dict[str, object] = {
    "expected_documents": 0,
    "documents_loaded": 0,
    "chunks_total": 0,
    "failed_documents": [],
}


def load_corpus() -> None:
    """Read every .txt in corpus/ and ingest it.  Filename sans extension = document_id.

    Each file gets CORPUS_LOAD_ATTEMPTS tries: the OpenAI embedding call fails transiently, and
    a skipped file leaves the API serving a silently incomplete corpus.
    """
    if not CORPUS_DIR.is_dir():
        logger.info("No corpus/ directory found — skipping auto-load.")
        return

    txt_files = sorted(CORPUS_DIR.glob("*.txt"))  # sorted for deterministic order
    if not txt_files:
        logger.info("corpus/ exists but contains no .txt files.")
        return

    _corpus_status["expected_documents"] = len(txt_files)
    loaded, failed_docs = 0, []

    for path in txt_files:
        document_id = path.stem                    # "POL-114.txt" → "POL-114"
        for attempt in range(1, CORPUS_LOAD_ATTEMPTS + 1):
            try:
                text = path.read_text(encoding="utf-8")
                result = run_ingest(
                    IngestRequest(document_id=document_id, text=text),
                )
                logger.info(
                    "Loaded %s → %d chunks (replaced %d)%s",
                    document_id, result.chunks_added, result.chunks_replaced,
                    f" on attempt {attempt}" if attempt > 1 else "",
                )
                loaded += 1
                break
            except Exception:
                if attempt < CORPUS_LOAD_ATTEMPTS:
                    logger.warning(
                        "Attempt %d/%d failed for %s — retrying.",
                        attempt, CORPUS_LOAD_ATTEMPTS, path.name,
                    )
                    continue
                logger.exception(
                    "Failed to load %s after %d attempts — skipping.",
                    path.name, CORPUS_LOAD_ATTEMPTS,
                )
                failed_docs.append(document_id)

    _corpus_status["documents_loaded"] = loaded
    _corpus_status["failed_documents"] = failed_docs
    _corpus_status["chunks_total"] = store_chunk_count()

    logger.info(
        "Corpus auto-load complete: %d loaded, %d failed, %d total chunks in store.%s",
        loaded, len(failed_docs), _corpus_status["chunks_total"],
        f"  DEGRADED — missing: {', '.join(failed_docs)}" if failed_docs else "",
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    warn_if_unconfigured()   # loud if the memory store is not durable

    # SELECT 1 before anything claims the store works. A wrong DATABASE_URL used to be
    # invisible: /health read the configured backend and answered "ok". Probing at startup
    # means the log and /health both report a measurement.
    result = memory_probe()
    if result["reachable"]:
        logger.info(
            "Memory store: %s - SELECT 1 answered. %d stories remembered.",
            memory_backend(), story_count(),
        )
        init_store()
    else:
        logger.warning(
            "Memory store: %s is NOT reachable (%s). /ping will still classify, but nothing "
            "will be remembered and /health reports status=degraded. This is the difference "
            "between 'configured for Postgres' and 'Postgres answers'.",
            memory_backend(), result["error"],
        )

    load_corpus()
    yield


app = FastAPI(title="AI Eng Bootcamp API", lifespan=lifespan)


@app.get("/")
def root():
    """Landing hint for deployed URL."""
    return {
        "service": "AI Eng Bootcamp API",
        "health": "/health",
        "docs": "/docs",
        "estimate": "POST /estimate",
        "analyze": "POST /analyze",
        "ask": "POST /ask",
        "ingest": "POST /ingest",
        "search": "POST /search",
        "ping": "POST /ping",
        "repo": "https://github.com/imanmshahi/ai-eng-bootcamp",
    }


@app.get("/health")
def health():
    """Heartbeat plus corpus completeness plus a live memory probe. No OpenAI call.

    status is "degraded" when any corpus file failed to ingest, or when the memory store does
    not answer. Without the first, a process serving 32 of 40 chunks answered "ok" and every
    refusal about the missing document looked legitimate (F6 in evals/FINDINGS.md).

    memory_reachable closes the gap CLAUDE.md rule 4 names: memory_backend says what was
    configured, which is not a claim that anything answered. A wrong DATABASE_URL used to read
    "memory_backend": "postgres" with status "ok". Now SELECT 1 runs on every call, so the
    endpoint reports what the component has rather than what it was told to be. stories_remembered
    is -1 when the table cannot be read, which is a different failure from an empty store.
    """
    failed = _corpus_status["failed_documents"]
    memory = memory_probe()
    reachable = bool(memory["reachable"])
    now = datetime.now(timezone.utc)
    return {
        "status": "degraded" if (failed or not reachable) else "ok",
        "started_at": _STARTED_AT.isoformat(),
        "uptime_seconds": round((now - _STARTED_AT).total_seconds(), 1),
        "memory_backend": memory_backend(),
        "memory_reachable": reachable,
        **({"memory_error": memory["error"]} if memory["error"] else {}),
        "stories_remembered": story_count() if reachable else -1,
        "documents_loaded": _corpus_status["documents_loaded"],
        "chunks_total": _corpus_status["chunks_total"],
        "expected_documents": _corpus_status["expected_documents"],
        **({"failed_documents": failed} if failed else {}),
    }


@app.post("/estimate", response_model=EstimateResponse)
def estimate(body: EstimateRequest):
    """Estimate model cost for a workload — powers the first Streamlit app."""
    try:
        return run_estimate(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(body: AnalyzeRequest):
    """Analyze a prompt → complexity, cost broad range, and closer delta."""
    try:
        return run_analyze(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/ingest", response_model=IngestResponse)
def ingest(body: IngestRequest):
    """Chunk + embed text into the in-memory RAG store."""
    try:
        return run_ingest(body)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Embedding call failed. Check your OpenAI key, billing, and network.",
        ) from exc


@app.post("/search", response_model=SearchResponse)
def search(body: SearchRequest):
    """Retrieve the top-k chunks most similar to the question (no LLM)."""
    try:
        return run_search(body)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Embedding call failed. Check your OpenAI key, billing, and network.",
        ) from exc


@app.post("/ping", response_model=PingResponse)
def ping(body: PingRequest):
    """Screen a news item: classify against the corpus, apply the write gate, remember or skip.

    The response says what happened rather than what was attempted — persisted, skipped_reason
    and memory_reachable are part of the contract, so a verdict that was classified and dropped
    cannot be mistaken for one that was remembered.
    """
    try:
        return run_screen(body.item_text, body.source_urls)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        error_name = type(exc).__name__
        if error_name == "AuthenticationError":
            raise HTTPException(status_code=401, detail="Invalid OpenAI API key.") from exc
        if error_name == "RateLimitError":
            raise HTTPException(status_code=402, detail="OpenAI account has no credits left.") from exc
        raise HTTPException(
            status_code=502,
            detail="Classification failed. Check billing, network, and try again.",
        ) from exc


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest):
    """Answer a question using OpenAI."""
    try:
        return ask_openai(body.question)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        error_name = type(exc).__name__
        if error_name == "AuthenticationError":
            raise HTTPException(
                status_code=401,
                detail=(
                    "Invalid OpenAI API key. Use a key from "
                    "https://platform.openai.com/api-keys (starts with sk-proj- or sk-). "
                    "Cursor keys (sk-crsr-) will not work here."
                ),
            ) from exc
        if error_name == "RateLimitError":
            raise HTTPException(
                status_code=402,
                detail=(
                    "OpenAI account has no credits left. Add billing at "
                    "https://platform.openai.com/settings/organization/billing"
                ),
            ) from exc
        raise HTTPException(
            status_code=502,
            detail="Model call failed. Check billing, network, and try again.",
        ) from exc
