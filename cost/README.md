# 100-review cost and runtime calculator

- **Offline replay (default, no API key, no model calls):**
  `.venv/bin/python cost/calculator.py`. This recomputes [report.md](report.md) and [usage.csv](usage.csv) from [pilot_calls.jsonl](pilot_calls.jsonl) × [rates.csv](rates.csv), and projects the full run from [assumptions.json](assumptions.json).
  - What-if: `--rates-multiplier 2` doubles the API subtotal; measured time and local costs are unchanged. `--budget 3` shows over-budget warnings.
- **Explicit paid pilot:** `.venv/bin/python cost/calculator.py --run-pilot`. This runs the real pipeline on `data/cost_100.csv`: cold (empty result cache, 1 worker) and then warm (saved results). It refreshes `runs/`, `pilot_calls.jsonl` and `pilot_records.jsonl`.
- **Measured:** cold 38.8 s, $0.0352, 104 calls, 0 failed. Warm 1.9 s, 0 new calls, $0.
- **Projection checked against reality:** the base case for the chosen scope (66,079 texts) was $4.65 / 1.04 h. The measured full run cost $4.04 and took about 1.3 h with 4 workers.
- **Controls:** budget reservations, a shared rate limiter, retry-once on invalid output, a circuit breaker, and a 1% advisor cap. All are implemented in `pipeline/enrich.py` and `pipeline/runtime.py` and tested in `evals/system_tests.json`.
- Local compute (laptop, SQLite/Python) is **unknown, not zero**. Jev rates come from third-party listings; reconcile them with the TypeSafe dashboard.
