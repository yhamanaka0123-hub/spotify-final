"""Assemble the standardized grading/ folder from a finished run. No model calls.

    .venv/bin/python -m pipeline.export --run-dir runs/full --out grading
"""
import argparse
import gzip
import json
import shutil
from pathlib import Path

from pipeline.contract import sha_file
from pipeline.enrich import LABEL_CONFIG

ROOT = Path(__file__).resolve().parent.parent
FULL_CSV = ROOT / "data" / "spotify_reviews_18months.csv"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    out, src = args.out, args.run_dir / "out"
    out.mkdir(parents=True, exist_ok=True)

    run = {"version": "a5-audit-v1", "analysis_count": 660622, "analysis_sha256": sha_file(FULL_CSV),
           "classification_input_fields": ["review_text"], "allow_multi_issue": False,
           "label_config": LABEL_CONFIG,
           "declared_scope": ("All 660,622 source IDs are accounted for. A seeded random sample of distinct texts "
                              "(plus every golden-50 text) covering 100,000 review IDs was classified; identical "
                              "texts reuse one validated result via cache_source_id. The 13 empty texts are "
                              "quarantined as empty_review_text; all other unclassified rows are quarantined as "
                              "not_classified_outside_budget_scope.")}
    (out / "run.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")

    with open(src / "records.jsonl", "rb") as f, gzip.open(out / "records.jsonl.gz", "wb", compresslevel=9) as g:
        shutil.copyfileobj(f, g)
    (out / "records.jsonl").unlink(missing_ok=True)
    for name in ("membership.csv", "ranking.csv", "claims.csv"):
        shutil.copy(src / name, out / name)
    shutil.copy(args.run_dir / "calls.jsonl", out / "calls.jsonl")
    for name in ("checkpoint_before.json", "checkpoint_after.json"):
        p = args.run_dir / name
        if p.exists():
            shutil.copy(p, out / name)
        else:
            print(f"WARNING: {p} missing")
    if not (out / "ingestion.json").exists():
        print("WARNING: run data/check_submission.py profile to create grading/ingestion.json")
    print("grading folder:", sorted(p.name for p in out.iterdir()))


if __name__ == "__main__":
    main()
