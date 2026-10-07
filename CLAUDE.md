# ai-eng-bootcamp — Iman (TAI Labs cohort 19)

## Current task: Week 2 assignment (Maven), extend Week 1, don't rebuild
1. POST /ingest: text + document_id (required) → chunk with overlap → embed (text-embedding-3-small) → UPSERT with metadata.
   Chunk IDs = f"{document_id}-{i}". Re-ingesting a document replaces its old chunks.
2. POST /search: question + k → top-k chunks with scores. No LLM. (Retrieval test.)
3. Upgrade the existing POST /ask: retrieve → context-only prompt → cite chunk IDs → refuse with a fixed sentence when the answer isn't in the context.
   Keep the Week 1 spend guard, tokens_used, cost_usd. Add citations: list[str] and refused: bool to AskResponse.
4. corpus/ folder re-ingested on startup (the in-memory store is wiped when Render sleeps or redeploys). Add COPY corpus to the Dockerfile.
5. Streamlit page with Ingest + Ask, pointed at the live API.

## Rules
- I'm learning: explain each change in plain words before making it.
- Test retrieval before wiring the LLM.
- Never read, print or commit .env. Never put keys in code.
- Windows: line-ending noise shows ~40 "modified" files. Only stage files we actually changed.
- Ignore docs/week2-*.md (an older notebook-based Week 2).