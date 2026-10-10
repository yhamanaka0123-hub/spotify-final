# 100-review cost and runtime calculator — report

Generated offline from saved measurements (`cost/pilot_calls.jsonl` × `cost/rates.csv`). Rates multiplier: **1.0**. No API calls were made to produce this report.

## Measured on the 100-review pilot

- Input: `data/cost_100.csv`, SHA-256 `c884ac3b9be5066995d5063f96ad9af6e5e082975788c1684c4f6b6ea661dd0e` (manifest matches)
- IDs: 100; completed 100; failed/quarantined 0; unique texts 100 (no exact duplicates in this sample); result-cache hits on the warm run: 100 of 100 texts
- Label config: `jev-1.13.0+jevq-v1+schema-v1+advisor:claude-sonnet-5-5@0.5`; workers: 1; enrichment batch: 1 review per Jev request; advisor/verify batches ≤ 20/25 reviews per Claude request

| Run | Wall-clock s | Stage seconds | New calls (enrich/verify/group/memo) | Failed calls | API cost |
|---|---|---|---|---|---|
| cold | 38.819 | {"prepare": 0.033, "enrich_jev": 13.97, "enrich_advisor": 5.756, "verify": 5.902, "group_rank_memo_export": 13.124} | 101/1/1/1 | 0 | $0.0352 |
| warm | 1.92 | {"prepare": 0.0, "enrich_jev": 0.109, "enrich_advisor": 1.803, "verify": 0.0, "group_rank_memo_export": 0.007} | 0/0/0/0 | 0 | $0.0000 |

- Cold: cost per 1,000 input rows **$0.3522**, per completed record **$0.0003522**, throughput 2.58 rows/s end-to-end.
- Warm: **0 new enrichment calls**, incremental cost $0.0000.

### By stage (cold)

| Stage | Provider model | Attempts | Failed | Input tok | Output tok | Cost | Summed call s |
|---|---|---|---|---|---|---|---|
| advisor | `claude-sonnet-5-5` | 1 | 0 | 1642 | 276 | $0.0060 | 2.9 |
| enrich | `jev-1.13.0` | 100 | 0 | 113987 | 19658 | $0.0048 | 13.7 |
| group | `claude-haiku-5-5` | 1 | 0 | 3581 | 500 | $0.0006081 | 4.2 |
| memo | `claude-sonnet-5-5` | 1 | 0 | 6085 | 1083 | $0.0230 | 8.9 |
| verify | `claude-haiku-5-5` | 1 | 0 | 2590 | 1041 | $0.0007795 | 5.9 |

Summed call seconds can exceed wall-clock time when calls overlap.

### Rates used (editable `cost/rates.csv`)

| Model | Item | USD per unit | Source | Checked |
|---|---|---|---|---|
| `jev-1.13.0` | input_tokens | 0.0000000420 | https://flaviocopes.com/jev-pricing/ (third-party; no official TypeSafe price page found) | 2026-10-10 |
| `jev-1.13.0` | output_tokens | 0.0000000000 | https://flaviocopes.com/jev-pricing/ (output tokens listed as free) | 2026-10-10 |
| `claude-haiku-5-5` | input_tokens | 0.0000001000 | https://platform.claude.com/docs/en/about-claude/pricing | 2026-10-10 |
| `claude-haiku-5-5` | output_tokens | 0.0000005000 | https://platform.claude.com/docs/en/about-claude/pricing | 2026-10-10 |
| `claude-sonnet-5-5` | input_tokens | 0.0000020000 | https://platform.claude.com/docs/en/about-claude/pricing | 2026-10-10 |
| `claude-sonnet-5-5` | output_tokens | 0.0000100000 | https://platform.claude.com/docs/en/about-claude/pricing | 2026-10-10 |

Jev pricing is from third-party listings (no official TypeSafe price page found); reconcile with the TypeSafe dashboard. Local compute (SQLite/Python on a laptop) is **unknown**, not zero.

## Full-run estimates

Budget: **$10.00**. Unit costs measured on the cold pilot: Jev $0.0000479/text, advisor $0.0020/review, verify $0.0000390/review, group+memo fixed $0.0236 once. Throughput: 7.2 Jev texts/s per worker, max workers 4, shared cap 18 req/s.

Every scenario accounts for all 660,622 rows: 13 empty texts are quarantined (`empty_review_text`); rows outside the classified scope are quarantined with an explicit reason.

| Scenario | Case | Texts classified | IDs covered | Enrich | Advisor | Verify | Fixed | Total | Hours | Budget |
|---|---|---|---|---|---|---|---|---|---|---|
| chosen_scope_100k_ids | base | 66,079 | 100,000 | $3.2268 | $1.3579 | $0.0398 | $0.0236 | **$4.6480** | 1.04 | ok |
| chosen_scope_100k_ids | conservative | 66,079 | 100,000 | $3.4799 | $4.3932 | $0.0429 | $0.0236 | **$7.9395** | 1.87 | ok |
| full_with_exact_text_reuse | base | 484,189 | 660,609 | $23.6439 | $9.9499 | $0.0795 | $0.0236 | **$33.6969** | 7.62 | ⚠️ OVER |
| full_with_exact_text_reuse | conservative | 484,189 | 660,609 | $25.4984 | $32.1908 | $0.0857 | $0.0236 | **$57.7985** | 13.70 | ⚠️ OVER |
| full_without_reuse | base | 660,609 | 660,609 | $32.2589 | $13.5753 | $0.0795 | $0.0236 | **$45.9372** | 10.40 | ⚠️ OVER |
| full_without_reuse | conservative | 660,609 | 660,609 | $34.7890 | $43.9199 | $0.0857 | $0.0236 | **$78.8183** | 18.69 | ⚠️ OVER |

Cases: base = 2% retries, 1% advisor fallback; conservative = 10% retries, 3% advisor fallback, 60% throughput. The output-token cap per request, maximum workers and the advisor cap are set in `cost/assumptions.json` and enforced in `pipeline/enrich.py` (spend reservations, rate limiter, circuit breaker).

