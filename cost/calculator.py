"""100-review cost/runtime calculator.

OFFLINE REPLAY (default, no API key, no model calls):
    .venv/bin/python cost/calculator.py
Recomputes every cost from cost/pilot_calls.jsonl (raw usage) x cost/rates.csv (editable dated rates),
projects the full run from cost/assumptions.json, and writes cost/report.md + cost/usage.csv.
Try: --rates-multiplier 2  (API subtotal doubles; measured time and local costs unchanged).

EXPLICIT PAID PILOT (makes real API calls; requires .env keys):
    .venv/bin/python cost/calculator.py --run-pilot
Runs the real pipeline on data/cost_100.csv cold (empty result cache, 1 worker) and warm (saved results),
then refreshes pilot_calls.jsonl / pilot_records.jsonl.
"""
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUNS = {"cold": HERE / "runs" / "cold", "warm": HERE / "runs" / "warm"}


def load_rates(mult):
    rates, meta = {}, {}
    with open(HERE / "rates.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rates[(row["model"], row["item"])] = float(row["price_usd_per_unit"]) * mult
            meta[(row["model"], row["item"])] = row
    return rates, meta


def run_pilot():
    py = sys.executable
    for name, extra in (("cold", ["--fresh"]), ("warm", [])):
        if name == "cold" and RUNS["cold"].exists():
            shutil.rmtree(RUNS["cold"])
        if name == "warm":  # warm run starts from the cold run's saved downstream artifacts
            if RUNS["warm"].exists():
                shutil.rmtree(RUNS["warm"])
            shutil.copytree(RUNS["cold"], RUNS["warm"], ignore=shutil.ignore_patterns("calls.jsonl", "run_summary.json"))
        subprocess.run([py, "-m", "pipeline.run", "--input", "data/cost_100.csv", "--db", "work/pilot.db",
                        "--run-dir", str(RUNS[name]), "--budget", "0.50", "--verify-sample", "20", "--workers", "1",
                        *extra], cwd=ROOT, check=True)
    collect()


def collect():
    """Copy raw pilot evidence into the cost/ folder files the instructor checks."""
    with open(HERE / "pilot_calls.jsonl", "w", encoding="utf-8") as out:
        for name, d in RUNS.items():
            p = d / "calls.jsonl"
            if p.exists():
                for line in open(p, encoding="utf-8"):
                    out.write(json.dumps({"run_id": f"pilot-{name}", **json.loads(line)}) + "\n")
    shutil.copy(RUNS["cold"] / "out" / "records.jsonl", HERE / "pilot_records.jsonl")


def refresh_section(rates, budget):
    """Estimate refreshes at the 500 and 10,000 checkpoints, plus the measured full run (all offline from saved logs)."""
    def load(path):
        return [json.loads(l) for l in open(path, encoding="utf-8")] if path.exists() else []

    def priced(c):
        if c["input_tokens"] is None:
            return 0.0
        return c["input_tokens"] * rates[(c["model"], "input_tokens")] + (c["output_tokens"] or 0) * rates[(c["model"], "output_tokens")]

    rows = []
    cp = load(ROOT / "runs" / "checkpoint_500" / "calls.jsonl")
    s500 = json.loads((ROOT / "runs" / "checkpoint_500" / "run_summary.json").read_text())
    full = load(ROOT / "grading" / "calls.jsonl")
    initial = [c for c in full if c["phase"] == "initial" and c["role"] == "enrich" and not c.get("advisor")]
    for name, calls, secs, workers in (
            ("checkpoint_500 (2 workers)", cp, s500["stage_seconds"]["enrich_jev"], 2),
            ("first 10,000 texts of the full run (4 workers)", initial,
             max(c["started_at"] + c["duration_s"] for c in initial) - min(c["started_at"] for c in initial), 4)):
        jev = [c for c in calls if c["role"] == "enrich" and not c.get("advisor")]
        ok = [c for c in jev if c["outcome"] == "succeeded"]
        per_text = sum(priced(c) for c in ok) / max(1, len(ok))
        rps = len(jev) / max(1e-9, secs)
        n = 66079
        rows.append((name, len(ok), per_text, rps, n * per_text, n / rps / 3600))
    out = ["", "## Estimate refreshes at 500 and 10,000 (measured, offline)", "",
           "| Checkpoint | Jev texts | Jev $/text | Texts/s | Projected Jev cost, 66,079 texts | Projected hours |",
           "|---|---|---|---|---|---|"]
    for name, n, pt, rps, cost, hours in rows:
        out.append(f"| {name} | {n:,} | {money(pt)} | {rps:.1f} | {money(cost)} | {hours:.2f} |")
    if full:
        total = sum(priced(c) for c in full)
        out += ["", f"**Measured full run** (`grading/calls.jsonl`, {len(full):,} attempts, "
                    f"{sum(c['outcome'] == 'failed' for c in full)} failed): **{money(total)}** at these rates. "
                    f"Budget ${budget:.2f}: {'within' if total <= budget else 'OVER'}."]
    return out


def money(x):
    if x is None:
        return "unknown"
    return f"${x:,.7f}" if 0 < abs(x) < 0.001 else f"${x:,.4f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-pilot", action="store_true", help="PAID: execute the real cold/warm pilot first")
    ap.add_argument("--rates-multiplier", type=float, default=1.0, help="scale every API rate (what-if)")
    ap.add_argument("--budget", type=float, help="override assumptions.json budget_usd")
    args = ap.parse_args()
    if args.run_pilot:
        run_pilot()
    elif not (HERE / "pilot_calls.jsonl").exists():
        collect()

    rates, meta = load_rates(args.rates_multiplier)
    A = json.loads((HERE / "assumptions.json").read_text(encoding="utf-8"))
    budget = args.budget if args.budget is not None else A["budget_usd"]
    calls = [json.loads(l) for l in open(HERE / "pilot_calls.jsonl", encoding="utf-8")]
    summaries = {n: json.loads((d / "run_summary.json").read_text()) for n, d in RUNS.items()}
    records = [json.loads(l) for l in open(HERE / "pilot_records.jsonl", encoding="utf-8")]
    cost100 = ROOT / "data" / "cost_100.csv"
    input_sha = hashlib.sha256(cost100.read_bytes()).hexdigest()
    manifest_sha = json.loads((ROOT / "data" / "manifest.json").read_text())["files"]["cost_100.csv"]["sha256"]

    # ---- measured: usage x rates, per call and per stage ----
    usage_rows, by_stage = [], defaultdict(lambda: defaultdict(float))
    for c in calls:
        stage = "advisor" if c.get("advisor") else c["role"]
        key = (c["run_id"], stage, c["model"])
        by_stage[key]["attempts"] += 1
        by_stage[key]["failed"] += c["outcome"] == "failed"
        by_stage[key]["review_ids"] += len(c["review_ids"])
        if c["input_tokens"] is None:
            by_stage[key]["usage_missing"] += 1
            usage_rows.append({**{k: c[k] for k in ("run_id", "request_id", "role", "model", "outcome")},
                               "stage": stage, "item": "usage_unavailable", "units": "", "price": "", "cost_usd": ""})
            continue
        for item, units in (("input_tokens", c["input_tokens"]), ("output_tokens", c["output_tokens"] or 0)):
            price = rates[(c["model"], item)]
            cost = units * price
            by_stage[key][item] += units
            by_stage[key]["cost"] += cost
            usage_rows.append({"run_id": c["run_id"], "request_id": c["request_id"], "role": c["role"],
                               "model": c["model"], "outcome": c["outcome"], "stage": stage, "item": item,
                               "units": units, "price": price, "cost_usd": round(cost, 10)})
        by_stage[key]["seconds"] += c.get("duration_s") or 0
    with open(HERE / "usage.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(usage_rows[0]))
        w.writeheader()
        w.writerows(usage_rows)

    def run_cost(run_id):
        return sum(v["cost"] for (r, _, _), v in by_stage.items() if r == run_id)

    cold_cost, warm_cost = run_cost("pilot-cold"), run_cost("pilot-warm")
    cold, warm = summaries["cold"], summaries["warm"]
    completed = sum(r["status"] == "completed" for r in records)
    failed = sum(r["status"] != "completed" for r in records)

    # ---- unit costs measured on the cold pilot ----
    def stage(name):
        v = [v for (r, s, _), v in by_stage.items() if r == "pilot-cold" and s == name]
        return v[0] if v else defaultdict(float)
    jev, adv, ver = stage("enrich"), stage("advisor"), stage("verify")
    jev_per_text = jev["cost"] / max(1, jev["attempts"] - jev["failed"])
    adv_per_text = adv["cost"] / max(1, adv["review_ids"])
    ver_per_review = ver["cost"] / max(1, ver["review_ids"])
    fixed = stage("group")["cost"] + stage("memo")["cost"]
    jev_rate_1w = (jev["attempts"]) / max(1e-9, cold["stage_seconds"]["enrich_jev"])

    # ---- projections ----
    proj = []
    for sname, s in A["scenarios"].items():
        for cname, c in A["cases"].items():
            n = s["texts_to_classify"]
            enrich_cost = n * jev_per_text * (1 + c["retry_rate"])
            advisor_cost = n * c["advisor_fraction"] * adv_per_text * (1 + c["retry_rate"])
            verify_cost = s["verify_sample"] * ver_per_review * (1 + c["retry_rate"])
            total = enrich_cost + advisor_cost + verify_cost + fixed
            rps = min(A["max_workers"] * jev_rate_1w, A["jev_max_requests_per_second"]) * c["throughput_factor"]
            hours = n * (1 + c["retry_rate"]) / rps / 3600
            proj.append({"scenario": sname, "case": cname, "texts": n, "ids": s["ids_covered"],
                         "enrich": enrich_cost, "advisor": advisor_cost, "verify": verify_cost, "fixed": fixed,
                         "total": total, "hours": hours, "over_budget": total > budget})

    L = []
    L.append("# 100-review cost and runtime calculator — report\n")
    L.append(f"Generated offline from saved measurements (`cost/pilot_calls.jsonl` × `cost/rates.csv`). "
             f"Rates multiplier: **{args.rates_multiplier}**. No API calls were made to produce this report.\n")
    L.append("## Measured on the 100-review pilot\n")
    L.append(f"- Input: `data/cost_100.csv`, SHA-256 `{input_sha}`"
             + (f" (manifest {'matches' if manifest_sha == input_sha else 'DIFFERS: ' + str(manifest_sha)})" if manifest_sha else ""))
    L.append(f"- IDs: {len(records)}; completed {completed}; failed/quarantined {failed}; "
             f"unique texts 100 (no exact duplicates in this sample); "
             f"result-cache hits on the warm run: {100 - (warm.get('jev_completed') or 0)} of 100 texts")
    L.append(f"- Label config: `{cold['label_config']}`; workers: {cold['workers']}; enrichment batch: 1 review per Jev "
             f"request; advisor/verify batches ≤ 20/25 reviews per Claude request")
    L.append("")
    L.append("| Run | Wall-clock s | Stage seconds | New calls (enrich/verify/group/memo) | Failed calls | API cost |")
    L.append("|---|---|---|---|---|---|")
    for name, s, cost in (("cold", cold, cold_cost), ("warm", warm, warm_cost)):
        roles = s["new_calls_by_role"]
        L.append(f"| {name} | {s['wall_seconds']} | {json.dumps(s['stage_seconds'])} | "
                 f"{roles['enrich']}/{roles['verify']}/{roles['group']}/{roles['memo']} | {s['new_failed_calls']} | "
                 f"{money(cost)} |")
    L.append("")
    L.append(f"- Cold: cost per 1,000 input rows **{money(cold_cost * 10)}**, per completed record "
             f"**{money(cold_cost / max(1, completed))}**, throughput {100 / cold['wall_seconds']:.2f} rows/s end-to-end.")
    L.append(f"- Warm: **{warm['new_calls_by_role']['enrich']} new enrichment calls**, incremental cost {money(warm_cost)}.")
    L.append("")
    L.append("### By stage (cold)\n")
    L.append("| Stage | Provider model | Attempts | Failed | Input tok | Output tok | Cost | Summed call s |")
    L.append("|---|---|---|---|---|---|---|---|")
    for (r, s, m), v in sorted(by_stage.items()):
        if r != "pilot-cold":
            continue
        L.append(f"| {s} | `{m}` | {int(v['attempts'])} | {int(v['failed'])} | {int(v['input_tokens'])} | "
                 f"{int(v['output_tokens'])} | {money(v['cost'])} | {v['seconds']:.1f} |")
    L.append("\nSummed call seconds can exceed wall-clock time when calls overlap.\n")
    L.append("### Rates used (editable `cost/rates.csv`)\n")
    L.append("| Model | Item | USD per unit | Source | Checked |")
    L.append("|---|---|---|---|---|")
    for (m, item), row in meta.items():
        L.append(f"| `{m}` | {item} | {rates[(m, item)]:.10f} | {row['source']} | {row['checked']} |")
    L.append("\nJev pricing is from third-party listings (no official TypeSafe price page found); reconcile with the "
             "TypeSafe dashboard. Local compute (SQLite/Python on a laptop) is **unknown**, not zero.\n")
    L.append("## Full-run estimates\n")
    L.append(f"Budget: **${budget:.2f}**. Unit costs measured on the cold pilot: Jev {money(jev_per_text)}/text, "
             f"advisor {money(adv_per_text)}/review, verify {money(ver_per_review)}/review, group+memo fixed "
             f"{money(fixed)} once. Throughput: {jev_rate_1w:.1f} Jev texts/s per worker, max workers "
             f"{A['max_workers']}, shared cap {A['jev_max_requests_per_second']} req/s.\n")
    L.append("Every scenario accounts for all 660,622 rows: 13 empty texts are quarantined (`empty_review_text`); "
             "rows outside the classified scope are quarantined with an explicit reason.\n")
    L.append("| Scenario | Case | Texts classified | IDs covered | Enrich | Advisor | Verify | Fixed | Total | Hours | Budget |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for p in proj:
        flag = "⚠️ OVER" if p["over_budget"] else "ok"
        L.append(f"| {p['scenario']} | {p['case']} | {p['texts']:,} | {p['ids']:,} | {money(p['enrich'])} | "
                 f"{money(p['advisor'])} | {money(p['verify'])} | {money(p['fixed'])} | **{money(p['total'])}** | "
                 f"{p['hours']:.2f} | {flag} |")
    L.append("\nCases: base = 2% retries, 1% advisor fallback; conservative = 10% retries, 3% advisor fallback, "
             "60% throughput. The output-token cap per request, maximum workers and the advisor cap are set in "
             "`cost/assumptions.json` and enforced in `pipeline/enrich.py` (spend reservations, rate limiter, "
             "circuit breaker).\n")
    L.extend(refresh_section(rates, budget))
    (HERE / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
