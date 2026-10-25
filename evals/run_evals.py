"""Run the code-based checks over a trace file and write evals/results_v1.json.

    python evals/run_evals.py                      # evals/traces_v1.jsonl -> evals/results_v1.json
    python evals/run_evals.py --traces X --out Y
    python evals/run_evals.py --verbose            # also print the reason for every failure

No LLM calls and no network: this reads a JSONL file and applies regexes, so it is free to run
and safe to run in CI.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.checks import CHECKS, TARGETS, over_refusal_rate, run_all  # noqa: E402

DEFAULT_TRACES = ROOT / "evals" / "traces_v1.jsonl"
DEFAULT_OUT = ROOT / "evals" / "results_v1.json"
DEFAULT_LABELS = ROOT / "evals" / "labels_v1.jsonl"


def load_traces(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_labels(path: Path) -> dict[str, dict]:
    """id -> label row from the labelling page. Missing file is fine: nothing is labelled yet."""
    labels: dict[str, dict] = {}
    if not path.exists():
        return labels
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("id"):
                labels[row["id"]] = row
    return labels


def merge_labels(traces: list[dict], labels: dict[str, dict]) -> list[dict]:
    """Attach `answerable` to each trace so checks keep their one-argument signature.

    `answerable` is a property of the question, not of a run, so the same labels file applies to
    every trace version — v1 labels score v2 traces unchanged.
    """
    for t in traces:
        row = labels.get(t.get("id", ""), {})
        t["answerable"] = (row.get("answerable") or "").strip()
    return traces


def evaluate(traces: list[dict]) -> dict:
    """Per-trace results plus overall counts, in the shape written to results_v1.json."""
    per_trace = []
    per_check = {name: {"passed": 0, "failed": 0, "failed_ids": []} for name in CHECKS}

    for t in traces:
        trace_id = t.get("id", "?")
        results = run_all(t)
        checks_out = {}
        for name, (passed, reason) in results.items():
            checks_out[name] = {"passed": passed, "reason": reason}
            bucket = per_check[name]
            bucket["passed" if passed else "failed"] += 1
            if not passed:
                bucket["failed_ids"].append(trace_id)

        failed_here = [n for n, r in checks_out.items() if not r["passed"]]
        per_trace.append(
            {
                "id": trace_id,
                "question": t.get("question", ""),
                "answerable": t.get("answerable", ""),
                "refused": bool(t.get("refused")),
                "n_citations": len(t.get("citations") or []),
                "n_retrieved": len(t.get("retrieved") or []),
                "checks": checks_out,
                "failed_checks": failed_here,
                "all_passed": not failed_here,
            }
        )

    clean = sum(1 for r in per_trace if r["all_passed"])
    return {
        "traces_evaluated": len(per_trace),
        "checks_run": list(CHECKS),
        "targets": TARGETS,
        "over_refusal": over_refusal_rate(traces),
        "counts": {
            "traces_all_checks_passed": clean,
            "traces_with_at_least_one_failure": len(per_trace) - clean,
            "total_check_runs": len(per_trace) * len(CHECKS),
            "total_failures": sum(len(r["failed_checks"]) for r in per_trace),
            "per_check": per_check,
        },
        "traces": per_trace,
    }


def print_summary(report: dict, verbose: bool = False) -> None:
    names = report["checks_run"]
    short = {n: n.replace("_", " ")[:14] for n in names}

    print(f"\n{report['traces_evaluated']} traces x {len(names)} checks "
          f"= {report['counts']['total_check_runs']} check runs\n")

    # Per-trace grid.
    head = f"{'id':<5}" + "".join(f"{short[n]:<16}" for n in names)
    print(head)
    print("-" * len(head))
    for row in report["traces"]:
        line = f"{row['id']:<5}"
        for n in names:
            line += f"{'PASS' if row['checks'][n]['passed'] else 'FAIL':<16}"
        print(line)

    # Per-check totals.
    print("\nper check")
    print("-" * 72)
    print(f"{'check':<30}{'target':<42}{'pass':>5}{'fail':>6}")
    for n in names:
        b = report["counts"]["per_check"][n]
        print(f"{n:<30}{report['targets'].get(n, ''):<42}{b['passed']:>5}{b['failed']:>6}")

    # Over-refusal rate — the one number that needs the human labels.
    o = report["over_refusal"]
    print("\nover-refusal (needs answerable labels)")
    print("-" * 72)
    if o["rate"] is None:
        print(f"  rate: n/a - {o['traces_labelled']} of "
              f"{o['traces_labelled'] + o['traces_unlabelled']} traces have an answerable label,")
        print("        and none is answerable=Yes. Label them in the Trace Labeller page.")
    else:
        pct = 100 * o["rate"]
        print(f"  over-refusal rate: {o['wrongly_refused']} / {o['answerable_yes']} = {pct:.1f}%"
              "   (wrongly-refused / answerable)")
        if o["wrongly_refused_ids"]:
            print(f"  wrongly refused  : {', '.join(o['wrongly_refused_ids'])}")
        if o["traces_unlabelled"]:
            print(f"  not evaluated    : {o['traces_unlabelled']} trace(s) with no answerable label")

    c = report["counts"]
    print("-" * 72)
    print(f"traces with every check passing : {c['traces_all_checks_passed']}"
          f" / {report['traces_evaluated']}")
    print(f"total check failures            : {c['total_failures']}")

    failures = [(r["id"], n, r["checks"][n]["reason"])
                for r in report["traces"] for n in r["failed_checks"]]
    if failures:
        print("\nfailures")
        print("-" * 72)
        for trace_id, name, reason in failures:
            print(f"  {trace_id}  {name}: {reason}")
    else:
        print("\nNo check failures. Note what this does and does not mean: C1, C4 and C5 in")
        print("evals/TAXONOMY.md are not covered by any code-based check.")

    if verbose:
        print("\nall reasons")
        print("-" * 72)
        for row in report["traces"]:
            print(f"  {row['id']}")
            for n in names:
                mark = "ok  " if row["checks"][n]["passed"] else "FAIL"
                print(f"    {mark} {n}: {row['checks'][n]['reason']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--traces", type=Path, default=DEFAULT_TRACES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--labels", type=Path, default=DEFAULT_LABELS,
                    help="label rows from the Trace Labeller page (supplies `answerable`)")
    ap.add_argument("--verbose", action="store_true", help="print every check's reason")
    args = ap.parse_args()

    # Resolve before use: a relative path like "evals/traces_v1.jsonl" is not a subpath of ROOT
    # until it is absolute, and the report records paths relative to ROOT.
    args.traces = args.traces.resolve()
    args.out = args.out.resolve()
    args.labels = args.labels.resolve()

    if not args.traces.exists():
        print(f"No trace file at {args.traces}", file=sys.stderr)
        return 1

    traces = load_traces(args.traces)
    if not traces:
        print(f"{args.traces} is empty", file=sys.stderr)
        return 1

    labels = load_labels(args.labels)
    traces = merge_labels(traces, labels)

    report = evaluate(traces)
    report["traces_file"] = str(args.traces.relative_to(ROOT))
    report["labels_file"] = str(args.labels.relative_to(ROOT)) if args.labels.exists() else None

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print_summary(report, verbose=args.verbose)
    print(f"\nWrote {args.out.relative_to(ROOT)}")
    # Exit 0 even with failures: this is a measurement, not a gate. Flip to a non-zero exit
    # once the known failures are triaged and you want CI to hold the line.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
