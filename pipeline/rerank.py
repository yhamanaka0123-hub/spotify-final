"""Regenerate the baseline ranking from the committed grading/ files only. No database, no API key,
no model calls. Compares the result with grading/ranking.csv and grading/claims.csv.

    python3 -m pipeline.rerank --grading grading
"""
import argparse
import csv
import gzip
import json
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grading", default="grading", type=Path)
    args = ap.parse_args()
    g = args.grading
    severity = {}
    with gzip.open(g / "records.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["status"] == "completed" and r["intent"] in ("complaint", "cancellation"):
                severity[r["review_id"]] = r["severity"]
    agg = defaultdict(lambda: [0, 0])
    for row in csv.DictReader(open(g / "membership.csv", encoding="utf-8")):
        agg[row["issue_id"]][0] += 1
        agg[row["issue_id"]][1] += severity[row["review_id"]]
    ranking = []
    for i, (issue, (n, s)) in enumerate(sorted(agg.items(), key=lambda kv: (-kv[1][1], kv[0])), 1):
        mean = (Decimal(s) / Decimal(n)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        ranking.append({"rank": str(i), "issue_id": issue, "complaint_count": str(n), "severity_sum": str(s),
                        "mean_severity": str(mean), "priority_score": str(s)})
    saved = list(csv.DictReader(open(g / "ranking.csv", encoding="utf-8")))
    by_issue = {r["issue_id"]: r for r in ranking}
    claims_ok = all(by_issue[c["issue_id"]][c["metric"]] == c["value"]
                    for c in csv.DictReader(open(g / "claims.csv", encoding="utf-8")))
    print("rank issue_id complaint_count severity_sum mean_severity priority_score")
    for r in ranking:
        print(" ".join(r.values()))
    print(f"\nmatches grading/ranking.csv: {ranking == saved}; every claims.csv value matches: {claims_ok}")


if __name__ == "__main__":
    main()
