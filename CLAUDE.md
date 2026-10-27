# ai-eng-bootcamp — Iman (TAI Labs cohort 19)

## Rules that must never be violated

These are absolute. They came from real incidents in this repo — the findings in
`evals/FINDINGS.md` are the evidence. Breaking one is a defect, not a style choice.

1. **Never print the value of any environment variable, and never print `.env` keys either.**
   A malformed line makes a secret appear as a *key name*: a line holding a bare connection
   string with no `KEY=` prefix is parsed by python-dotenv as a key with a `None` value, so
   "printing only the keys" prints the credential. This happened twice here. Report
   **presence or absence only** — `True`/`False`, a count, a length, never the text. When a
   URL must be shown, redact it through `server/memory.py: redacted()` and verify the password
   is absent from the output.

2. **Never stage with `git add .`** — nor `git add -A`, nor `git commit -a`. Stage named paths
   only, then show what is staged with `git diff --cached --name-status` before committing.
   Windows line endings make roughly 40 files look modified, so a blanket add sweeps in changes
   nobody reviewed.

3. **Never write a credential into `.env.example` or any tracked file.** `.env.example` holds
   placeholders and is committed; `.env` holds real values and is gitignored. Real connection
   strings go in `.env` only, or are injected by the platform — on Render via `fromDatabase` in
   `render.yaml`, so the credential never enters the repo. Before any commit touching config,
   check: `git grep -lE "dpg-[a-z0-9]{6,}|://[^:/@ ]+:[^@ ]+@" -- . ':!CLAUDE.md'` must return
   nothing. The `':!CLAUDE.md'` exclusion is required, not a convenience: this rule quotes the
   pattern, so the file always matches itself, and a check that always returns one hit is a check
   whose first real hit gets dismissed as the usual noise. Documentation placeholders must be
   written so they do not match either — see the docstring note in `server/memory.py`.

4. **A component must report its own state, not what it was configured to be.** `/health` names
   the memory backend, the document and chunk counts, and whether each is *reachable*. "I was
   told to use Postgres" is not the same claim as "Postgres answers". A status endpoint that
   reports intent instead of fact is how F6 served 32 of 40 chunks while returning `{"status":
   "ok"}`.
   *Gap closed:* `/health` now runs `SELECT 1` on every call and reports `memory_reachable`
   alongside `memory_backend`, with `status: "degraded"` when the store does not answer and
   `stories_remembered: -1` when the table cannot be read. `memory_backend` still states what is
   *configured* — the two claims are deliberately separate, because only one of them is a
   measurement. Verified against a deliberately unreachable URL: `"memory_reachable": false`,
   `"memory_error": "OperationalError"`, `status: "degraded"`.

5. **A fallback must warn. Never degrade silently from the configured backend.** A fallback that
   keeps the process running is fine; a fallback nobody is told about is a defect. An unset
   `DATABASE_URL` logs a WARNING naming the SQLite path and saying it will not survive a Render
   restart (F9). The test is simple: if the degraded mode would pass a local demo and fail in
   production, the log must say so loudly enough that the demo is not mistaken for proof.

6. **Build metadata is not a secret.** `/health` may report the commit SHA from
   `RENDER_GIT_COMMIT`, the start time, and the uptime. This is an explicit allowance alongside
   rule 1, not an exception to it — rule 1 still forbids printing any other environment variable
   value.
   *Scope, so this does not widen by precedent:* the allowance covers `RENDER_GIT_COMMIT` and
   nothing else. `RENDER_SERVICE_NAME`, `RENDER_INSTANCE_ID` and every other platform variable
   stay under rule 1 until listed here. Why this is worth allowing: without a build identifier, a
   `/health` check cannot say *which* build answered it, which is how F11 passed a live check
   against a stale deployment and concluded auto-deploy was broken.

**The pattern these guard against.** Six times in this repo a failure has reported itself as a
success — F2, F4, F6, F7, F9, and the dotenv line that absorbed a malformed config entry without
error. Every one produced *well-formed* output that a schema check would pass. What each lacked
was a statement of what the component actually had. Prefer checks keyed on structure over
wording, and make components declare their own state.

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