"""Trace Labeller — read evals/traces_v1.jsonl, label one trace at a time, save as you go.

Offline page: it never calls the API. The retrieval previews are rebuilt locally by
re-chunking corpus/ with the server's own chunker, so the text shown is the text that
was retrieved.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # so the page also runs when launched directly
    sys.path.insert(0, str(ROOT))

from server.rag import chunk_id, chunk_text  # noqa: E402
TRACES_PATH = ROOT / "evals" / "traces_v1.jsonl"
LABELS_PATH = ROOT / "evals" / "labels_v1.jsonl"
CORPUS_DIR = ROOT / "corpus"

# Must match server/schemas.py IngestRequest defaults — the values startup ingest uses.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

LABELS = ["OK", "RETRIEVAL", "MODEL", "REFUSED-WRONGLY", "REFUSED-RIGHTLY"]
ANSWERABLE = ["Yes", "No", "Partly"]


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Tables as markdown — pandas is blocked by Application Control on this machine."""
    def cell(v: object) -> str:
        return str(v).replace("|", chr(92) + "|").replace(chr(10), " ")

    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return chr(10).join([head, rule, *body])

st.set_page_config(page_title="Trace Labeller", page_icon="🏷️", layout="wide")
st.title("Trace Labeller")
st.caption("One trace at a time. Every change is written to `evals/labels_v1.jsonl` straight away.")


# ── Loading ───────────────────────────────────────────────────────────
@st.cache_data
def load_traces() -> list[dict]:
    if not TRACES_PATH.exists():
        return []
    with TRACES_PATH.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


@st.cache_data
def load_chunk_texts() -> dict[str, str]:
    """chunk_id -> text, rebuilt from corpus/ with the same chunker the API uses."""
    texts: dict[str, str] = {}
    if not CORPUS_DIR.is_dir():
        return texts
    for path in sorted(CORPUS_DIR.glob("*.txt")):
        document_id = path.stem
        chunks = chunk_text(path.read_text(encoding="utf-8"), CHUNK_SIZE, CHUNK_OVERLAP)
        for i, chunk in enumerate(chunks):
            texts[chunk_id(document_id, i)] = chunk
    return texts


def read_labels() -> dict[str, dict]:
    """Last line per id wins, so an older file with duplicates still resumes correctly."""
    labels: dict[str, dict] = {}
    if not LABELS_PATH.exists():
        return labels
    with LABELS_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("id"):
                labels[row["id"]] = {
                    "id": row["id"],
                    "label": row.get("label", ""),
                    "note": row.get("note", ""),
                    "answerable": row.get("answerable", ""),
                }
    return labels


def write_labels(labels: dict[str, dict], order: list[str]) -> None:
    """Rewrite the whole file in trace order — one line per id, no stale duplicates."""
    LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(labels[tid], ensure_ascii=False) for tid in order if tid in labels]
    LABELS_PATH.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


traces = load_traces()
if not traces:
    st.error(f"No traces found at `{TRACES_PATH.relative_to(ROOT)}`.")
    st.stop()

chunk_texts = load_chunk_texts()
trace_ids = [t["id"] for t in traces]

if "labels" not in st.session_state:
    st.session_state.labels = read_labels()
if "cursor" not in st.session_state:
    # Resume on the first unlabelled trace.
    unlabelled = [i for i, tid in enumerate(trace_ids) if tid not in st.session_state.labels]
    st.session_state.cursor = unlabelled[0] if unlabelled else 0

labels: dict[str, dict] = st.session_state.labels


def save(trace_id: str) -> None:
    """on_change callback: pull the widget values for this trace and persist them.

    Either field alone is worth saving — answerable is often the easier call, and the two are
    independent judgements.
    """
    label = st.session_state.get(f"label_{trace_id}") or ""
    answerable = st.session_state.get(f"answerable_{trace_id}") or ""
    note = (st.session_state.get(f"note_{trace_id}") or "").strip()
    if not label and not answerable:
        return
    labels[trace_id] = {
        "id": trace_id,
        "label": label,
        "note": note,
        "answerable": answerable,
    }
    write_labels(labels, trace_ids)


# ── Navigation ────────────────────────────────────────────────────────
cursor = st.session_state.cursor
trace = traces[cursor]
trace_id = trace["id"]

nav_prev, nav_pos, nav_next = st.columns([1, 2, 1])
with nav_prev:
    if st.button("← Previous", use_container_width=True, disabled=cursor == 0):
        st.session_state.cursor -= 1
        st.rerun()
with nav_pos:
    st.markdown(
        f"<div style='text-align:center;padding-top:0.4rem'>"
        f"<b>{trace_id}</b> — trace {cursor + 1} of {len(traces)}</div>",
        unsafe_allow_html=True,
    )
with nav_next:
    if st.button("Next →", use_container_width=True, disabled=cursor == len(traces) - 1):
        st.session_state.cursor += 1
        st.rerun()

done = sum(1 for tid in trace_ids if tid in labels)
st.progress(done / len(traces), text=f"{done} / {len(traces)} labelled")
st.divider()

# ── The trace ─────────────────────────────────────────────────────────
citations = trace.get("citations") or []

st.subheader("Question")
st.write(trace.get("question", ""))

st.subheader("Answer")
st.write(trace.get("answer", ""))

meta_left, meta_right = st.columns(2)
with meta_left:
    st.markdown("**Citations**")
    st.write(", ".join(citations) if citations else "_none_")
with meta_right:
    st.markdown("**Refused**")
    st.write("🚫 yes" if trace.get("refused") else "✅ no")

retrieved = trace.get("retrieved") or []
with st.expander(f"Retrieval ({len(retrieved)} chunks)"):
    if not retrieved:
        st.caption("No retrieval recorded for this trace.")
    else:
        rows = []
        for r in retrieved:
            cid = r.get("chunk_id", "")
            preview = " ".join(chunk_texts.get(cid, "").split())[:220]
            rows.append(
                [
                    cid,
                    f"{r.get('score', 0.0):.4f}",
                    "✓" if cid in citations else "",
                    (preview + "…") if preview else "— not found in corpus/ —",
                ]
            )
        st.markdown(md_table(["chunk_id", "score", "cited", "text preview"], rows))

st.divider()

# ── Controls ──────────────────────────────────────────────────────────
existing = labels.get(trace_id, {})

st.radio(
    "Answerable — does the corpus contain the answer to this question?",
    ANSWERABLE,
    index=ANSWERABLE.index(existing["answerable"])
    if existing.get("answerable") in ANSWERABLE
    else None,
    key=f"answerable_{trace_id}",
    horizontal=True,
    on_change=save,
    args=(trace_id,),
    help="Your judgement about the corpus, independent of what the model did. "
    "Partly = one part of a multi-part question is covered and another is not. "
    "Nothing is preselected on purpose.",
)

st.radio(
    "Label",
    LABELS,
    index=LABELS.index(existing["label"]) if existing.get("label") in LABELS else None,
    key=f"label_{trace_id}",
    horizontal=True,
    on_change=save,
    args=(trace_id,),
)
st.text_input(
    "Note (one line)",
    value=existing.get("note", ""),
    key=f"note_{trace_id}",
    placeholder="What went wrong, or why this is fine…",
    on_change=save,
    args=(trace_id,),
)

saved = labels.get(trace_id)
if saved:
    bits = []
    if saved.get("answerable"):
        bits.append(f"answerable **{saved['answerable']}**")
    if saved.get("label"):
        bits.append(f"label **{saved['label']}**")
    st.success("Saved: " + ", ".join(bits))
    if not saved.get("answerable"):
        st.warning("No `answerable` yet — the over-refusal rate only counts traces that have one.")
else:
    st.info("Pick either radio — it saves on click.")

# ── Summary ───────────────────────────────────────────────────────────
st.divider()
left, right = st.columns(2)
with left:
    st.subheader("Counts by label")
    counts = [
        [name, sum(1 for row in labels.values() if row.get("label") == name)] for name in LABELS
    ]
    counts.append(["unlabelled", len(traces) - sum(c[1] for c in counts)])
    st.markdown(md_table(["label", "count"], counts))
with right:
    st.subheader("Counts by answerable")
    a_counts = [
        [name, sum(1 for row in labels.values() if row.get("answerable") == name)]
        for name in ANSWERABLE
    ]
    a_counts.append(["unset", len(traces) - sum(c[1] for c in a_counts)])
    st.markdown(md_table(["answerable", "count"], a_counts))
st.caption(f"Writing to `{LABELS_PATH.relative_to(ROOT)}`")
