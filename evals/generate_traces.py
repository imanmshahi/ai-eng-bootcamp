"""Replay evals/questions_v1.txt against a running API and write a traces JSONL file.

    python evals/generate_traces.py --out evals/traces_v2.jsonl

Calls POST /search (for the retrieved list, which /ask does not return) and POST /ask per
question, and writes one trace per line in the same shape as traces_v1.jsonl.

This spends money: 20 /ask calls plus 20 embeddings, roughly a cent on gpt-4o-mini.  It reads no
secrets — the key lives in the server's own environment, and nothing here prints it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUESTIONS = ROOT / "evals" / "questions_v1.txt"
DEFAULT_OUT = ROOT / "evals" / "traces_v2.jsonl"
DEFAULT_BASE = "http://127.0.0.1:8000"

# Lines look like "q07  What is the minimum share…"; "#" starts a comment.
_QUESTION_LINE = re.compile(r"^(q\d+)\s+(.*\S)\s*$")


def load_questions(path: Path) -> list[tuple[str, str]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _QUESTION_LINE.match(line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def one_trace(base: str, qid: str, question: str, k: int, timeout: int) -> dict:
    search = requests.post(f"{base}/search", json={"question": question, "k": k}, timeout=timeout)
    search.raise_for_status()
    hits = search.json().get("results", [])

    ask = requests.post(f"{base}/ask", json={"question": question}, timeout=timeout)
    ask.raise_for_status()
    a = ask.json()

    return {
        "id": qid,
        "question": question,
        "answer": a.get("answer", ""),
        "citations": a.get("citations", []),
        "refused": bool(a.get("refused")),
        "tokens_used": a.get("tokens_used", 0),
        # Keep the same three fields v1 recorded — chunk text is rebuilt from corpus/ when needed.
        "retrieved": [
            {
                "chunk_id": h.get("chunk_id", ""),
                "document_id": h.get("document_id", ""),
                "score": round(float(h.get("score", 0.0)), 4),
            }
            for h in hits
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--base", default=DEFAULT_BASE, help="API base URL")
    ap.add_argument("--k", type=int, default=5, help="k for /search; /ask uses its own k")
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    questions = load_questions(args.questions.resolve())
    if not questions:
        print(f"No questions parsed from {args.questions}", file=sys.stderr)
        return 1

    try:
        health = requests.get(f"{args.base}/health", timeout=10)
        health.raise_for_status()
    except requests.RequestException as exc:
        print(f"API not reachable at {args.base}: {exc}", file=sys.stderr)
        return 1

    traces, failed = [], []
    for qid, question in questions:
        try:
            trace = one_trace(args.base, qid, question, args.k, args.timeout)
        except requests.RequestException as exc:
            # Keep going: one bad call should not cost the other 19.
            print(f"  {qid}  ERROR {exc}", file=sys.stderr)
            failed.append(qid)
            continue
        traces.append(trace)
        flag = "REFUSED" if trace["refused"] else f"{len(trace['citations'])} cite(s)"
        print(f"  {qid}  {flag:<12} {trace['tokens_used']:>6} tokens")

    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for t in traces:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(traces)} trace(s) to {out.relative_to(ROOT)}")
    if failed:
        print(f"Failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
