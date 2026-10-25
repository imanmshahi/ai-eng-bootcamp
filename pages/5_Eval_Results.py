"""Eval Results — BEFORE (v1) vs AFTER (v3) for the line-boundary chunking fix.

Reads the JSON the eval runner writes. No API calls, no pandas (its DLL is blocked by
Application Control in this venv), so every table is rendered as markdown.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # so the page also runs when launched directly
    sys.path.insert(0, str(ROOT))

from evals.checks import declined  # noqa: E402

BEFORE_RESULTS = ROOT / "evals" / "results_v1.json"
AFTER_RESULTS = ROOT / "evals" / "results_v3.json"
BEFORE_TRACES = ROOT / "evals" / "traces_v1.jsonl"
AFTER_TRACES = ROOT / "evals" / "traces_v3.jsonl"
LABELS = ROOT / "evals" / "labels_v1.jsonl"
RUNNER = ROOT / "evals" / "run_evals.py"

BEFORE_LABEL = "BEFORE (v1)"
AFTER_LABEL = "AFTER (v3)"

st.set_page_config(page_title="Eval Results", page_icon="📊", layout="wide")


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    """Tables as markdown — pandas is blocked by Application Control on this machine."""
    def cell(v: object) -> str:
        return str(v).replace("|", chr(92) + "|").replace(chr(10), " ")

    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return chr(10).join([head, rule, *body])


@st.cache_data
def load_json(path: str, mtime: float) -> dict:
    """mtime is in the cache key so a re-run of the suite invalidates this."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


@st.cache_data
def load_traces(path: str, mtime: float) -> dict[str, dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return {d["id"]: d for d in (json.loads(line) for line in fh if line.strip())}


def decline_state(trace: dict | None, result_row: dict) -> tuple[str, bool]:
    """(state, gave_up) where state is answered | hedged | refused.

    Distinguishing hedged from refused matters: a hedge still carries a partial answer and
    citations, so hedged -> refused is a loss of breadth that a plain declined/answered column
    cannot show (q13).
    """
    if trace is None:
        gave_up = bool(result_row.get("refused"))
        return ("refused" if gave_up else "answered"), gave_up
    gave_up, how = declined(trace)
    if not gave_up:
        return "answered", False
    return ("hedged" if how.startswith("hedged") else "refused"), True


def read(path: Path, loader):
    if not path.exists():
        return None
    return loader(str(path), path.stat().st_mtime)


st.title("Eval Results")
st.caption(
    "Line-boundary chunking fix (F1 root cause). "
    "BEFORE = `traces_v1.jsonl` at 40 chunks; AFTER = `traces_v3.jsonl` at 48 chunks. "
    "The answer path is unchanged between the two."
)

before = read(BEFORE_RESULTS, load_json)
after = read(AFTER_RESULTS, load_json)

missing = [p.name for p, d in ((BEFORE_RESULTS, before), (AFTER_RESULTS, after)) if d is None]
if missing:
    st.error(f"Missing results file(s): {', '.join(missing)}. Run the suite first.")
    st.code("python evals/run_evals.py --traces evals/traces_v3.jsonl --out evals/results_v3.json")
    st.stop()

# ── Headline: over-refusal rate ───────────────────────────────────────
ob, oa = before["over_refusal"], after["over_refusal"]


def pct(o: dict) -> str:
    return "n/a" if o["rate"] is None else f"{100 * o['rate']:.1f}%"


st.markdown(
    "<div style='text-align:center;margin:0.5rem 0 0.25rem'>"
    "<div style='font-size:0.95rem;letter-spacing:0.12em;text-transform:uppercase;opacity:0.65'>"
    "Over-refusal rate &nbsp;·&nbsp; wrongly refused / answerable</div></div>",
    unsafe_allow_html=True,
)

big_l, big_m, big_r = st.columns([3, 2, 3])


def big_number(col, caption: str, o: dict, colour: str) -> None:
    with col:
        detail = (
            "no answerable labels"
            if o["rate"] is None
            else f"{o['wrongly_refused']} of {o['answerable_yes']} answerable"
        )
        col.markdown(
            f"<div style='text-align:center'>"
            f"<div style='font-size:0.9rem;opacity:0.7;margin-bottom:-0.4rem'>{caption}</div>"
            f"<div style='font-size:5.5rem;font-weight:800;line-height:1.05;color:{colour}'>"
            f"{pct(o)}</div>"
            f"<div style='font-size:0.9rem;opacity:0.7'>{detail}</div></div>",
            unsafe_allow_html=True,
        )


big_number(big_l, BEFORE_LABEL, ob, "#c2410c")
big_number(big_r, AFTER_LABEL, oa, "#15803d")

with big_m:
    if ob["rate"] is None or oa["rate"] is None:
        arrow = "→"
    else:
        delta_pts = 100 * (oa["rate"] - ob["rate"])
        sign = "+" if delta_pts > 0 else ""
        arrow = (
            f"<div style='font-size:2.2rem;line-height:1'>→</div>"
            f"<div style='font-size:1.6rem;font-weight:700;color:"
            f"{'#15803d' if delta_pts < 0 else '#c2410c'}'>{sign}{delta_pts:.1f} pts</div>"
        )
    st.markdown(
        f"<div style='text-align:center;padding-top:2.6rem;opacity:0.9'>{arrow}</div>",
        unsafe_allow_html=True,
    )

wrong_before = ", ".join(ob["wrongly_refused_ids"]) or "none"
wrong_after = ", ".join(oa["wrongly_refused_ids"]) or "none"
fixed = [q for q in ob["wrongly_refused_ids"] if q not in oa["wrongly_refused_ids"]]
st.markdown(
    f"<div style='text-align:center;opacity:0.8;margin-top:0.25rem'>"
    f"wrongly refused — <b>before:</b> {wrong_before} &nbsp;·&nbsp; "
    f"<b>after:</b> {wrong_after}"
    + (f" &nbsp;·&nbsp; <b>fixed:</b> {', '.join(fixed)}" if fixed else "")
    + "</div>",
    unsafe_allow_html=True,
)

st.divider()

# ── Re-run the suite ──────────────────────────────────────────────────
run_col, note_col = st.columns([1, 4])
with run_col:
    run_clicked = st.button("Run checks now", type="primary", use_container_width=True)
with note_col:
    st.caption(
        f"Re-runs `evals/run_evals.py` on `{AFTER_TRACES.name}` and rewrites "
        f"`{AFTER_RESULTS.name}`, then reloads this page. Reads the trace file only — "
        "it makes no API calls and costs nothing."
    )

if run_clicked:
    with st.spinner("Running the five checks…"):
        proc = subprocess.run(
            [sys.executable, str(RUNNER),
             "--traces", str(AFTER_TRACES),
             "--out", str(AFTER_RESULTS),
             "--labels", str(LABELS)],
            capture_output=True, text=True, cwd=str(ROOT),
        )
    if proc.returncode == 0:
        st.success("Checks re-run.")
        with st.expander("Runner output"):
            st.code(proc.stdout or "(no output)")
        load_json.clear()
        load_traces.clear()
        st.rerun()
    else:
        st.error(f"Runner exited {proc.returncode}.")
        st.code((proc.stdout or "") + (proc.stderr or ""))

# ── All five checks ───────────────────────────────────────────────────
st.subheader("Checks")

names = after["checks_run"]
rows = []
for name in names:
    b = before["counts"]["per_check"].get(name, {"passed": 0, "failed": 0})
    a = after["counts"]["per_check"].get(name, {"passed": 0, "failed": 0})
    moved = a["passed"] - b["passed"]
    if moved > 0:
        marker = f"moved +{moved}"
    elif moved < 0:
        marker = f"REGRESSED {moved}"
    else:
        marker = "held"
    rows.append([
        f"`{name}`",
        after["targets"].get(name, ""),
        f"{b['passed']} / {before['traces_evaluated']}",
        f"{a['passed']} / {after['traces_evaluated']}",
        marker,
    ])

rows.append([
    "**traces fully clean**", "",
    f"**{before['counts']['traces_all_checks_passed']} / {before['traces_evaluated']}**",
    f"**{after['counts']['traces_all_checks_passed']} / {after['traces_evaluated']}**",
    "",
])

st.markdown(md_table(["check", "targets", BEFORE_LABEL, AFTER_LABEL, ""], rows))

# ── Per trace ─────────────────────────────────────────────────────────
st.subheader("Per trace")
st.caption(
    "`declined` covers all three routes a trace can give up — the `refused` flag, the fixed "
    "refusal sentence, or a hedge — because a hedged non-answer carries `refused: false` and "
    "would otherwise look like a clean answer here."
)

tb = read(BEFORE_TRACES, load_traces) or {}
ta = read(AFTER_TRACES, load_traces) or {}
labels = {r["id"]: r for r in (
    json.loads(line) for line in LABELS.read_text(encoding="utf-8").splitlines() if line.strip()
)} if LABELS.exists() else {}

by_id_before = {t["id"]: t for t in before["traces"]}
by_id_after = {t["id"]: t for t in after["traces"]}

trace_rows = []
for qid in sorted(set(by_id_before) | set(by_id_after)):
    rb, ra = by_id_before.get(qid, {}), by_id_after.get(qid, {})
    answerable = labels.get(qid, {}).get("answerable") or ra.get("answerable") or "—"

    sb, db = decline_state(tb.get(qid), rb)
    sa, da = decline_state(ta.get(qid), ra)

    if db and not da:
        movement = "**FIXED**"
    elif da and not db:
        movement = "**REGRESSED**"
    elif sb == "hedged" and sa == "refused":
        # Lost a partial answer. Not an over-refusal if labelled Partly, but still a loss.
        movement = "**narrowed**"
    elif sb == "refused" and sa == "hedged":
        movement = "widened"
    else:
        movement = ""

    # An over-refusal only counts where the human said the corpus has the answer.
    over_b = "yes" if qid in ob["wrongly_refused_ids"] else ""
    over_a = "yes" if qid in oa["wrongly_refused_ids"] else ""

    trace_rows.append([
        qid,
        answerable,
        f"{sb} ({rb.get('n_citations', 0)} cites)",
        f"{sa} ({ra.get('n_citations', 0)} cites)",
        movement,
        over_b,
        over_a,
        ", ".join(ra.get("failed_checks", [])) or "",
    ])

st.markdown(md_table(
    ["id", "answerable", f"{BEFORE_LABEL}", f"{AFTER_LABEL}", "moved",
     "over-refusal before", "over-refusal after", "checks failing after"],
    trace_rows,
))

st.caption(
    f"Sources: `{BEFORE_RESULTS.name}` · `{AFTER_RESULTS.name}` · labels from `{LABELS.name}`. "
    "Over-refusal counts only questions labelled answerable=Yes; Partly is recorded but not "
    "scored, which is why q13's move shows here without changing the headline."
)
