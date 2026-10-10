"""Orchestrator: input CSV -> prepare -> enrich -> verify -> group -> rank -> recommend -> export.

    .venv/bin/python -m pipeline.run --input data/cost_100.csv --db work/cost_100.db \
        --run-dir runs/pilot_cold --budget 0.50 --verify-sample 20 --fresh

Code owns dispatch, state, validation, budgets and logs; models only read language.
Rerunning without --fresh reuses saved results (zero new enrichment calls for completed texts).
"""
import argparse
import json
import sqlite3
import time
from pathlib import Path

from pipeline import downstream, enrich, prepare, verify
from pipeline.runtime import BudgetExceeded, Run, load_env


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--budget", required=True, type=float)
    ap.add_argument("--verify-sample", type=int, default=20)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--limit-texts", type=int)
    ap.add_argument("--fresh", action="store_true", help="re-ingest (empty result cache)")
    ap.add_argument("--phase", choices=["initial", "resume"], default="initial")
    args = ap.parse_args()

    load_env()
    stages, t0 = {}, time.time()
    run = Run(args.run_dir, args.budget, phase=args.phase)
    calls_before = sum(1 for _ in open(run.calls_path)) if run.calls_path.exists() else 0

    t = time.time()
    if args.fresh or not args.db.exists():
        report = prepare.ingest(args.input, args.db)
        args.db.with_suffix(".ingestion_report.json").write_text(json.dumps(report, indent=2) + "\n")
    stages["prepare"] = round(time.time() - t, 3)

    con = sqlite3.connect(args.db)
    enrich.ensure_scope(con, args.limit_texts, "a5-scope-v1")
    status = "completed"
    try:
        t = time.time()
        done, failed, _ = enrich.run_jev(con, run, args.workers, None)
        stages["enrich_jev"] = round(time.time() - t, 3)
        t = time.time()
        advised = enrich.run_advisor(con, run)
        stages["enrich_advisor"] = round(time.time() - t, 3)
        t = time.time()
        vpath = args.run_dir / "verify_report.json"
        if vpath.exists() and json.loads(vpath.read_text()).get("enrich_config") == enrich.LABEL_CONFIG \
                and not args.fresh:
            print("[verify] reused saved verification (same enrich config)")
        else:
            verify.verify(con, run, args.verify_sample, args.run_dir)
        stages["verify"] = round(time.time() - t, 3)
        t = time.time()
        result = downstream.run_downstream(con, run, args.run_dir / "out")
        stages["group_rank_memo_export"] = round(time.time() - t, 3)
    except BudgetExceeded as e:
        print(f"[run] STOP budget: {e}")
        status = "stopped_budget"
        done = failed = advised = None
        result = {}

    calls = [json.loads(l) for l in open(run.calls_path)] if run.calls_path.exists() else []
    new_calls = calls[calls_before:]
    summary = {
        "input": str(args.input), "db": str(args.db), "status": status, "fresh": args.fresh,
        "label_config": enrich.LABEL_CONFIG, "workers": args.workers, "phase": args.phase,
        "wall_seconds": round(time.time() - t0, 3), "stage_seconds": stages,
        "new_calls": len(new_calls),
        "new_calls_by_role": {r: sum(c["role"] == r for c in new_calls) for r in ("enrich", "verify", "group", "memo")},
        "new_failed_calls": sum(c["outcome"] == "failed" for c in new_calls),
        "new_cost_usd": round(sum(c.get("cost_usd") or 0 for c in new_calls), 6),
        "jev_completed": done, "jev_failed": failed, "advisor_relabelled": advised,
        "counts": result.get("counts"), "memo_problems": result.get("memo_problems"),
    }
    (args.run_dir / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
