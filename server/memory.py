"""Watchbird's long-term memory: where DATABASE_URL is read, and where the `stories` table lives.

Two halves:

* **Connection plumbing** — one place that resolves the URL, redacts it, and names the backend,
  so choosing between SQLite and Postgres is a URL change rather than a code change.
* **The store** — the `stories` table, the write gate, story identity, and
  whats_new_vs_before. One row per story, not per news item: the same story seen three times is
  one row with ping_count=3, which is what lets the agent say what changed since last time.

    DATABASE_URL=sqlite:///./watchbird.db     # default, local file
    DATABASE_URL=postgresql+psycopg://...     # Postgres (credentials, host, port, db name)

The Postgres form is written with an ellipsis on purpose. Spelled out in full it matches the
credential-scan pattern in CLAUDE.md rule 3, and a scan that always returns this file is a scan
whose one real hit would be read as the usual false positive.

SQLAlchemy is imported lazily inside engine() and _table(), so importing this module works
whether or not SQLAlchemy is installed — `describe()` and the warnings stay usable without it.

What is deliberately **not** stored: retrieved chunk text, raw tool output, and anything else the
corpus gave us. A story row holds only the classifier's own short fields plus the chunk IDs it
cited. Keeping corpus text out means the store cannot quietly become a second, stale copy of the
corpus that nobody re-ingests.
"""

from __future__ import annotations

import logging
import math
import os
import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("bootcamp")

ROOT = Path(__file__).resolve().parent.parent

# A local file, so the store works with nothing configured. Relative to wherever the process
# started, which is why describe() reports the resolved absolute path.
DEFAULT_DATABASE_URL = "sqlite:///./watchbird.db"


def db_url() -> str:
    """The configured database URL, or the SQLite default when DATABASE_URL is unset.

    Render hands out `postgresql://…` (and older tooling `postgres://…`), while SQLAlchemy with
    psycopg3 wants `postgresql+psycopg://…`. Normalising here means you can paste Render's string
    verbatim instead of hand-editing a credential, which is where typos and leaks come from.
    """
    raw = os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    for prefix in ("postgresql://", "postgres://"):
        if raw.startswith(prefix):
            return "postgresql+psycopg://" + raw[len(prefix):]
    return raw


def is_sqlite(url: str | None = None) -> bool:
    return (url or db_url()).startswith("sqlite")


def redacted(url: str | None = None) -> str:
    """The URL with any password replaced by ***, safe to log or print.

    A Postgres URL carries credentials. Everything user-facing goes through this, so a
    connection string never reaches a log, a traceback or the terminal in full.
    """
    raw = url or db_url()
    parts = urlsplit(raw)
    if not parts.password:
        return raw
    user = parts.username or ""
    host = parts.hostname or ""
    port = f":{parts.port}" if parts.port else ""
    netloc = f"{user}:***@{host}{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def sqlite_path(url: str | None = None) -> Path | None:
    """Absolute path of the SQLite file, or None for a non-SQLite URL."""
    raw = url or db_url()
    if not is_sqlite(raw):
        return None
    tail = raw.split("sqlite:///", 1)[-1] if "sqlite:///" in raw else ""
    if not tail or tail == ":memory:":
        return None
    return Path(tail).resolve()


def backend(url: str | None = None) -> str:
    """"sqlite" | "postgres" | the raw scheme for anything else. What /health reports."""
    scheme = urlsplit(url or db_url()).scheme.split("+")[0]
    if scheme.startswith("sqlite"):
        return "sqlite"
    if scheme in ("postgres", "postgresql"):
        return "postgres"
    return scheme or "unknown"


def warn_if_unconfigured() -> bool:
    """Log a WARNING when DATABASE_URL is unset. Returns True if the warning fired.

    The fallback to SQLite stays — it keeps the API runnable with nothing configured — but it is
    no longer silent. An unset DATABASE_URL on Render means the store lives on the container
    filesystem, which the free web service wipes on every restart and redeploy: memory that
    passes a local demo and loses everything in production. That is F9 in evals/FINDINGS.md, and
    the whole point of the warning is that the failure announces itself.
    """
    if os.getenv("DATABASE_URL"):
        logger.info("Memory store: postgres (DATABASE_URL is set).")
        return False

    path = sqlite_path()
    logger.warning(
        "DATABASE_URL is not set - memory store is falling back to SQLite at %s. "
        "This file is NOT durable on Render: the free web service has no persistent disk, so "
        "every restart or redeploy starts with an empty store. Set DATABASE_URL in .env "
        "locally, or uncomment the fromDatabase block in render.yaml to deploy.",
        path or DEFAULT_DATABASE_URL,
    )
    return True


def describe() -> dict[str, Any]:
    """What is configured, with no secrets — for /health, a startup log, or a sanity check."""
    url = db_url()
    path = sqlite_path(url)
    return {
        "configured": bool(os.getenv("DATABASE_URL")),
        "backend": backend(url),
        "url": redacted(url),
        "sqlite_file": str(path) if path else None,
        "sqlite_file_exists": path.exists() if path else None,
        "driver_installed": driver_installed(),
    }


def driver_installed() -> bool:
    """Is SQLAlchemy importable? SQLite needs nothing further; Postgres also needs psycopg."""
    try:
        import sqlalchemy  # noqa: F401
    except ImportError:
        return False
    return True


def engine(**kwargs: Any):
    """A SQLAlchemy Engine for db_url(). Raises a readable error if the driver is missing."""
    try:
        from sqlalchemy import create_engine
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise RuntimeError(
            "SQLAlchemy is not installed. Add it to requirements-api.txt and run:\n"
            "  .venv/Scripts/python.exe -m pip install 'sqlalchemy>=2.0' psycopg[binary]"
        ) from exc
    return create_engine(db_url(), **kwargs)


# ---------------------------------------------------------------------------
# Reachability
# ---------------------------------------------------------------------------

# Cached result of the last probe(), so /health reports a measurement rather than a guess.
# None means "never probed", which /health reports as unknown rather than as healthy.
_probe_result: dict[str, Any] = {"reachable": None, "error": None, "checked_at": None}


def probe() -> dict[str, Any]:
    """Run `SELECT 1` against the configured database and remember the answer.

    This is rule 4 of CLAUDE.md applied to the store: /health used to report the *configured*
    backend, so a wrong DATABASE_URL still read "memory_backend": "postgres" and the endpoint
    answered "ok". Reporting what was configured is not a claim that anything answered. Now the
    claim is a measurement: the query either came back or it did not.
    """
    result: dict[str, Any] = {
        "reachable": False,
        "error": None,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        from sqlalchemy import text

        with engine().connect() as conn:
            conn.execute(text("SELECT 1")).scalar()
        result["reachable"] = True
    except Exception as exc:
        # The message can embed the connection string, so only the exception type is kept.
        result["error"] = type(exc).__name__
    _probe_result.update(result)
    return dict(result)


def last_probe() -> dict[str, Any]:
    """The cached probe result without running a new query. What /health reads."""
    return dict(_probe_result)


# ---------------------------------------------------------------------------
# The stories table
# ---------------------------------------------------------------------------

# One row per story. Built lazily so importing this module never requires SQLAlchemy.
_metadata = None
_stories = None


def _table():
    """The `stories` Table object, defined once per process."""
    global _metadata, _stories
    if _stories is not None:
        return _stories

    from sqlalchemy import (
        JSON,
        Column,
        DateTime,
        Integer,
        MetaData,
        String,
        Table,
        Text,
    )

    _metadata = MetaData()
    _stories = Table(
        "stories",
        _metadata,
        # slug(instrument + jurisdiction + sorted fuels + eu_channel) - see story_key().
        Column("story_key", String(512), primary_key=True),
        Column("instrument", String(300), nullable=False),
        Column("jurisdiction", String(120), nullable=False),
        Column("fuels", JSON, nullable=False),            # sorted, lowercased list[str]
        Column("eu_channel", String(60), nullable=False),
        Column("first_seen", DateTime(timezone=True), nullable=False),
        Column("last_seen", DateTime(timezone=True), nullable=False),
        Column("stages_seen", JSON, nullable=False),      # list[str], append-only, in order
        Column("latest_stage", String(40), nullable=False),
        Column("source_urls", JSON, nullable=False),      # list[str] from the news item
        # The classifier's own one-line description of the news item. NOT corpus text:
        # what_happened is the model summarising the item it was handed, so no retrieved
        # chunk ever lands in the store.
        Column("last_summary", Text, nullable=False),
        Column("embedding", JSON, nullable=False),        # list[float] of what_happened
        Column("ping_count", Integer, nullable=False),
    )
    return _stories


def init_store() -> dict[str, Any]:
    """Create the `stories` table if it does not exist. Safe to call on every startup.

    Returns the outcome rather than raising, so a database that is down degrades the service
    instead of preventing it from booting - and /health says so.
    """
    try:
        _table().metadata.create_all(engine())
        return {"ready": True, "error": None}
    except Exception as exc:
        logger.warning(
            "Could not create or verify the stories table (%s). The memory store is "
            "UNAVAILABLE: /ping will classify but will not remember anything across "
            "restarts. /health reports memory_reachable=false.",
            type(exc).__name__,
        )
        return {"ready": False, "error": type(exc).__name__}


# ---------------------------------------------------------------------------
# Story identity
# ---------------------------------------------------------------------------

# Cosine similarity at or above which two what_happened texts are treated as the same story.
#
# UNVALIDATED. 0.85 is a guess carried over from common practice with
# text-embedding-3-small, not a number measured on this corpus. Nobody has built a labelled
# set of same-story / different-story pairs here, so it is not known how many distinct
# stories this merges or how many repeats it lets through as new. Treat every match at this
# threshold as unverified until that set exists.
SAME_STORY_COSINE = 0.85

# eu_channel is a closed list for the same reason stage is (F4): free text drifted run to run,
# and story_key is built from it, so "import duty" vs "import_duty" would split one story in two.
EU_CHANNELS: tuple[str, ...] = (
    "mandate",
    "target",
    "import_duty",
    "export_restriction",
    "subsidy",
    "certification",
    "other",
)

# The six stages, mirrored from agent/watchbird_agent.py. Duplicated rather than imported
# because that module imports google.adk at module scope, which the API must not require.
STAGES: tuple[str, ...] = (
    "proposed",
    "provisional",
    "definitive",
    "in_force",
    "amended",
    "expired",
)


def slug(text: str) -> str:
    """Lowercase, ASCII, hyphen-separated. Stable across wording that differs only in form."""
    folded = unicodedata.normalize("NFKD", text or "")
    ascii_only = folded.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", ascii_only.lower())).strip("-")


def normalise_fuels(fuels: Sequence[str] | None) -> list[str]:
    """Lowercased, de-duplicated, sorted - so fuel order in the reply cannot change the key."""
    seen = {(f or "").strip().lower() for f in (fuels or []) if (f or "").strip()}
    return sorted(seen)


# Fuel synonyms folded onto one canonical token per group.
#
# HAND-MADE from Iman's domain knowledge. Not derived from a standard, a dataset or the corpus:
# every line is a judgement that two names mean the same regulated thing, and the map is
# deliberately small so each entry can be argued about one at a time.
#
# Why this exists: story_key is built from the fuel set, so the classifier naming the same fuel
# two ways would split one story into two rows. On 2026-10-27 that happened - one item came back
# with ["SAF", "synthetic aviation fuel"] and the next with ["SAF"], the exact key missed, and
# recall survived only because the unvalidated 0.85 embedding threshold caught it at 0.8547.
#
# Note on the first group: the synthetic terms fold onto "saf", not onto a token of their own.
# They are *kinds of* SAF, not alternatives to it, so an item listing the umbrella plus the
# sub-kind must produce the same key as an item listing the umbrella alone.
#
# That fold has a cost, and it is recorded as **F10 (OPEN)** in evals/FINDINGS.md rather than
# left as a comment: a story about the ReFuelEU synthetic sub-target now shares a story_key with
# one about headline SAF shares, and under ReFuelEU those are distinct policy levers with
# different economics. The row keeps the classifier's own words in `fuels`, so the distinction
# stays readable - it just no longer decides identity. The fix is a `sub_target` value in
# EU_CHANNELS, deferred because it is a schema change.
CANONICAL_FUELS: dict[str, str] = {
    # Sustainable aviation fuel and its synthetic sub-kinds
    "saf": "saf",
    "sustainable aviation fuel": "saf",
    "synthetic aviation fuel": "saf",
    "e saf": "saf",                       # "e-SAF" after hyphens become spaces
    "esaf": "saf",                        # the same term written without a separator
    "rfnbo derived jet": "saf",
    "power to liquid jet": "saf",
    "e kerosene": "saf",
    # Hydrotreated vegetable oil
    "hvo": "hvo",
    "hydrotreated vegetable oil": "hvo",
    # FAME biodiesel
    "fame": "biodiesel",
    "biodiesel": "biodiesel",
}


def _fuel_lookup_form(fuel: str) -> str:
    """Lowercase, hyphens and punctuation to spaces, whitespace collapsed, trailing plural cut.

    Only for looking a name up in CANONICAL_FUELS, so "E-SAF", "e saf" and "e-SAFs" all find the
    same entry without needing three lines in the map.
    """
    text = unicodedata.normalize("NFKD", fuel or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return re.sub(r"s$", "", text) if text.endswith("s") and not text.endswith("ss") else text


def canonical_fuels(fuels: Sequence[str] | None) -> list[str]:
    """The fuel set reduced to canonical tokens, de-duplicated and sorted. What story_key uses.

    A fuel that is not in the map keeps its own cleaned name rather than being dropped or
    lumped into an "other" bucket: an unknown fuel is a distinct story, not a nameless one.
    """
    tokens = set()
    for fuel in fuels or []:
        form = _fuel_lookup_form(fuel)
        if form:
            tokens.add(CANONICAL_FUELS.get(form, form))
    return sorted(tokens)


def display_fuels(fuels: Sequence[str] | None) -> list[str]:
    """The classifier's own fuel names, trimmed and de-duplicated, for the row and the response.

    Stored instead of the canonical tokens so the row still shows that an item was specifically
    about synthetic aviation fuel, even though identity no longer turns on it.
    """
    out: list[str] = []
    seen: set[str] = set()
    for fuel in fuels or []:
        cleaned = (fuel or "").strip()
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            out.append(cleaned)
    return sorted(out, key=str.lower)


def normalise_channel(eu_channel: str | None) -> str:
    """Coerce eu_channel into EU_CHANNELS, warning when it had to be coerced.

    Rule 5: the fallback keeps the row writable, but it is not silent. An unrecognised channel
    means the classifier drifted off the closed list, and that is worth seeing in the log.
    """
    value = (eu_channel or "").strip().lower().replace(" ", "_").replace("-", "_")
    if value in EU_CHANNELS:
        return value
    logger.warning(
        "eu_channel %r is not one of %s - storing as 'other'. The classifier drifted off "
        "the closed list; story_key for this item is built from 'other'.",
        eu_channel, ", ".join(EU_CHANNELS),
    )
    return "other"


def story_key(
    instrument: str | None,
    jurisdiction: str | None,
    fuels: Sequence[str] | None,
    eu_channel: str | None,
) -> str:
    """Identity of a story: slug of instrument + jurisdiction + CANONICAL fuels + eu_channel.

    The fuel component runs through canonical_fuels(), so "synthetic aviation fuel" and "SAF"
    cannot key as two different stories. That is what keeps identity off the unvalidated
    embedding threshold: the exact key should carry a repeat story, and the embedding should be
    the fallback it was meant to be rather than the thing recall depends on.

    Returns "" when there is no instrument. An item with no instrument is not a story we can
    track, and an empty key must never be written.
    """
    if not (instrument or "").strip():
        return ""
    parts = [
        slug(instrument or ""),
        slug(jurisdiction or ""),
        "-".join(slug(f) for f in canonical_fuels(fuels)),
        slug(normalise_channel(eu_channel)),
    ]
    return "|".join(parts)


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity, 1.0 identical / 0.0 orthogonal. Same maths as server.rag."""
    if not a or not b:
        return 0.0
    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = math.sqrt(sum(ai * ai for ai in a))
    norm_b = math.sqrt(sum(bi * bi for bi in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# The write gate
# ---------------------------------------------------------------------------

GATE_MIN_CONFIDENCE = 0.6


def gate_reason(verdict: Mapping[str, Any]) -> str | None:
    """Why this verdict must NOT be stored, or None when all four conditions hold.

    All of these must be true to persist:
      * ping is true                 - a non-ping is not a story worth remembering
      * citations is non-empty       - an ungrounded verdict must not become a remembered fact
      * confidence >= 0.6            - below that the classification is a guess
      * stage is a valid enum value  - a drifted stage would corrupt stage-change detection

    A pure function on a mapping, with no database and no network, so the gate is testable on
    its own. That matters: the gate is the only thing standing between a hallucinated verdict
    and a row that every later run will treat as established history.
    """
    if not verdict.get("ping"):
        return "ping is false"

    citations = verdict.get("citations") or []
    if not citations:
        return "no citations - verdict is not grounded in retrieved chunks"

    raw_confidence = verdict.get("confidence")
    try:
        confidence = float(raw_confidence)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return f"confidence {raw_confidence!r} is not a number"
    if confidence < GATE_MIN_CONFIDENCE:
        # :g not :.2f - rounding to 2dp turned 0.5999 into the self-contradicting
        # "confidence 0.60 is below 0.6", a rejection message that argues against itself.
        return f"confidence {confidence:g} is below {GATE_MIN_CONFIDENCE}"

    stage = verdict.get("stage")
    if stage not in STAGES:
        return f"stage {stage!r} is not one of {', '.join(STAGES)}"

    if not story_key(
        verdict.get("instrument"),
        verdict.get("jurisdiction"),
        verdict.get("fuels"),
        verdict.get("eu_channel"),
    ):
        return "no instrument - nothing to key the story on"

    return None


# ---------------------------------------------------------------------------
# whats_new_vs_before
# ---------------------------------------------------------------------------

FIRST_TIME = "First time this story has appeared."
NOT_TRACKED = "Not tracked: no instrument was identified, so there is no story to compare against."


def _seen_date(row: Mapping[str, Any]) -> str:
    """The stored last_seen as a plain date. Falls back to the raw value if it is not a datetime."""
    value = row.get("last_seen")
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value)[:10] if value else "an earlier run"


def whats_new_vs_before(
    previous: Mapping[str, Any] | None,
    verdict: Mapping[str, Any],
) -> str:
    """One plain sentence about what changed, computed against the row as it was BEFORE this write.

    Order matters: this must be called while `previous` still holds the earlier run's values.
    Compute it after the update and every story looks unchanged, because the update has already
    overwritten the thing being compared.
    """
    if previous is None:
        if not story_key(
            verdict.get("instrument"),
            verdict.get("jurisdiction"),
            verdict.get("fuels"),
            verdict.get("eu_channel"),
        ):
            return NOT_TRACKED
        return FIRST_TIME

    when = _seen_date(previous)
    sentences: list[str] = []

    old_stage = previous.get("latest_stage")
    new_stage = verdict.get("stage")
    if new_stage and new_stage != old_stage:
        sentences.append(f"Moved from {old_stage} to {new_stage} since {when}.")
    else:
        sentences.append(f"Seen before on {when}, no stage change.")

    # Compared canonically, reported in the classifier's words: "synthetic aviation fuel" after
    # "SAF" is the same fuel named differently, not an addition, and saying otherwise would
    # invent a change on every rewording.
    added: list[str] = []
    known = set(canonical_fuels(previous.get("fuels")))
    new_fuels = [
        f for f in display_fuels(verdict.get("fuels"))
        if not set(canonical_fuels([f])) <= known
    ]
    if new_fuels:
        added.append("fuels " + ", ".join(new_fuels))

    old_jurisdiction = (previous.get("jurisdiction") or "").strip()
    new_jurisdiction = (verdict.get("jurisdiction") or "").strip()
    if new_jurisdiction and new_jurisdiction.lower() != old_jurisdiction.lower():
        added.append(f"jurisdiction {new_jurisdiction}")

    if added:
        sentences.append("Now also covers " + " and ".join(added) + ".")

    return " ".join(sentences)


# ---------------------------------------------------------------------------
# Lookup and write
# ---------------------------------------------------------------------------

def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row._mapping)


def find_story(
    conn: Any,
    key: str,
    embedding: Sequence[float] | None,
) -> tuple[dict[str, Any] | None, str | None, float | None]:
    """Locate the story this verdict belongs to.

    Exact story_key first - same instrument, jurisdiction, fuels and channel is the same story
    by construction. Only when that misses does the embedding comparison run, because the
    embedding route is the unvalidated one (SAME_STORY_COSINE).

    Returns (row, matched_by, score) with matched_by in "key" / "embedding" / None.
    """
    from sqlalchemy import select

    stories = _table()

    if key:
        hit = conn.execute(select(stories).where(stories.c.story_key == key)).first()
        if hit is not None:
            return _row_to_dict(hit), "key", 1.0

    if not embedding:
        return None, None, None

    # Linear scan. There are tens of stories, not millions; a pgvector index is the answer if
    # that ever changes, and it would also make the threshold measurable.
    best_row, best_score = None, 0.0
    for row in conn.execute(select(stories)):
        candidate = _row_to_dict(row)
        score = cosine(embedding, candidate.get("embedding") or [])
        if score > best_score:
            best_row, best_score = candidate, score

    if best_row is not None and best_score >= SAME_STORY_COSINE:
        return best_row, "embedding", best_score
    return None, None, best_score or None


def remember(
    verdict: Mapping[str, Any],
    *,
    embedding: Sequence[float] | None = None,
    source_urls: Sequence[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Apply the write gate, then insert or update one story row. Never raises on a bad verdict.

    whats_new_vs_before is computed on retrieval - before any write - so it describes the
    change rather than the state after it. A gated-out verdict still gets the comparison: the
    caller asked what is new, and the answer does not depend on whether we chose to store it.

    Returns what actually happened, not what was intended: persisted, the reason if it was
    skipped, and whether the store could be reached at all.
    """
    key = story_key(
        verdict.get("instrument"),
        verdict.get("jurisdiction"),
        verdict.get("fuels"),
        verdict.get("eu_channel"),
    )
    outcome: dict[str, Any] = {
        "story_key": key or None,
        "persisted": False,
        "skipped_reason": None,
        "matched_by": None,
        "match_score": None,
        "ping_count": 0,
        "store_error": None,
        "whats_new_vs_before": NOT_TRACKED if not key else FIRST_TIME,
    }

    reason = gate_reason(verdict)
    stamp = now or datetime.now(timezone.utc)

    try:
        from sqlalchemy import insert, update

        stories = _table()
        with engine().begin() as conn:
            previous, matched_by, score = find_story(conn, key, embedding)
            outcome["matched_by"] = matched_by
            outcome["match_score"] = round(score, 6) if score is not None else None
            outcome["whats_new_vs_before"] = whats_new_vs_before(previous, verdict)
            outcome["ping_count"] = int(previous.get("ping_count") or 0) if previous else 0

            if reason is not None:
                outcome["skipped_reason"] = reason
                logger.info(
                    "WRITE GATE skipped a verdict: %s. Nothing was stored; "
                    "whats_new_vs_before was still computed from the existing row.", reason,
                )
                return outcome

            # The row holds the classifier's own words; only story_key uses canonical tokens.
            fuels = display_fuels(verdict.get("fuels"))
            channel = normalise_channel(verdict.get("eu_channel"))
            stage = verdict.get("stage")
            # last_summary is the classifier's what_happened, never retrieved chunk text.
            summary = (verdict.get("what_happened") or "").strip()
            urls = sorted({u.strip() for u in (source_urls or []) if (u or "").strip()})
            vector = list(embedding or [])

            if previous is None:
                conn.execute(insert(stories).values(
                    story_key=key,
                    instrument=(verdict.get("instrument") or "").strip(),
                    jurisdiction=(verdict.get("jurisdiction") or "").strip(),
                    fuels=fuels,
                    eu_channel=channel,
                    first_seen=stamp,
                    last_seen=stamp,
                    stages_seen=[stage],
                    latest_stage=stage,
                    source_urls=urls,
                    last_summary=summary,
                    embedding=vector,
                    ping_count=1,
                ))
                outcome["ping_count"] = 1
            else:
                # Append-only history: stages_seen records the path, not just the destination,
                # so "moved from proposed to in_force" stays answerable later.
                stages_seen = list(previous.get("stages_seen") or [])
                if not stages_seen or stages_seen[-1] != stage:
                    stages_seen.append(stage)
                merged_fuels = display_fuels(list(previous.get("fuels") or []) + fuels)
                merged_urls = sorted(set(previous.get("source_urls") or []) | set(urls))
                count = int(previous.get("ping_count") or 0) + 1
                conn.execute(
                    update(stories)
                    .where(stories.c.story_key == previous["story_key"])
                    .values(
                        last_seen=stamp,
                        stages_seen=stages_seen,
                        latest_stage=stage,
                        fuels=merged_fuels,
                        source_urls=merged_urls,
                        last_summary=summary,
                        embedding=vector,
                        jurisdiction=(verdict.get("jurisdiction") or "").strip()
                        or previous.get("jurisdiction"),
                        ping_count=count,
                    )
                )
                outcome["ping_count"] = count
                outcome["story_key"] = previous["story_key"]

            outcome["persisted"] = True
            return outcome

    except Exception as exc:
        # The store being down must not look like a successful classification.
        outcome["store_error"] = type(exc).__name__
        outcome["skipped_reason"] = reason or f"memory store unreachable ({type(exc).__name__})"
        outcome["whats_new_vs_before"] = (
            "Unknown - the memory store could not be reached, so there is nothing to compare "
            "against. This is not the same as a story being new."
        )
        logger.warning(
            "Memory store write failed (%s). The verdict was NOT remembered and "
            "whats_new_vs_before is unknown, not 'first time'.", type(exc).__name__,
        )
        return outcome


def story_count() -> int:
    """How many stories are remembered right now. -1 when the store cannot be read."""
    try:
        from sqlalchemy import func, select

        with engine().connect() as conn:
            return int(conn.execute(select(func.count()).select_from(_table())).scalar() or 0)
    except Exception:
        return -1


if __name__ == "__main__":  # python -m server.memory
    import json

    print(json.dumps({**describe(), "probe": probe(), "stories": story_count()}, indent=2))
