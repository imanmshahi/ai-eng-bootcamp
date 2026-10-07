"""Week 1 server — /health, POST /ask, POST /estimate."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from server.analyze_service import run_analyze
from server.estimate_service import run_estimate
from server.openai_client import ask_openai
from server.rag import ingest as run_ingest, search as run_search
from server.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AskRequest,
    AskResponse,
    EstimateRequest,
    EstimateResponse,
    IngestRequest,
    IngestResponse,
    SearchRequest,
    SearchResponse,
)

logger = logging.getLogger("bootcamp")

# ---------------------------------------------------------------------------
# Startup: auto-load corpus/ into the RAG store
# ---------------------------------------------------------------------------

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"


def load_corpus() -> None:
    """Read every .txt in corpus/ and ingest it.  Filename sans extension = document_id."""
    if not CORPUS_DIR.is_dir():
        logger.info("No corpus/ directory found — skipping auto-load.")
        return

    txt_files = sorted(CORPUS_DIR.glob("*.txt"))  # sorted for deterministic order
    if not txt_files:
        logger.info("corpus/ exists but contains no .txt files.")
        return

    loaded, failed = 0, 0
    for path in txt_files:
        document_id = path.stem                    # "POL-114.txt" → "POL-114"
        try:
            text = path.read_text(encoding="utf-8")
            result = run_ingest(
                IngestRequest(document_id=document_id, text=text),
            )
            logger.info(
                "Loaded %s → %d chunks (replaced %d)",
                document_id, result.chunks_added, result.chunks_replaced,
            )
            loaded += 1
        except Exception:
            logger.exception("Failed to load %s — skipping.", path.name)
            failed += 1

    logger.info(
        "Corpus auto-load complete: %d loaded, %d failed, %d total chunks in store.",
        loaded, failed, loaded + failed,  # total files attempted
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
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
        "repo": "https://github.com/imanmshahi/ai-eng-bootcamp",
    }


@app.get("/health")
def health():
    """Heartbeat check. No OpenAI, no logic — just 'am I running?'"""
    return {"status": "ok"}


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
