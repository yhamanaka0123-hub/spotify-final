"""Write runs/<run>/run_manifest.json tying source checksum, code version, prompts, models, settings and
output checksums together. No model calls.

    .venv/bin/python -m pipeline.manifest --run-dir runs/full
"""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

from pipeline import downstream, enrich, labels, verify
from pipeline.contract import sha_file

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True, type=Path)
    args = ap.parse_args()
    args.run_dir = args.run_dir.resolve()
    files = [p for p in sorted((ROOT / "grading").iterdir()) if p.is_file()] + \
        [p for p in sorted((args.run_dir / "out").iterdir()) if p.is_file() and p.name != "records.jsonl"] + \
        [args.run_dir / n for n in ("verify_report.json", "run_summary.json") if (args.run_dir / n).exists()]
    manifest = {
        "run_id": "full-2026-10-10",
        "written_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "code_version": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(),
        "source": {"file": "data/spotify_reviews_18months.csv", "sha256": sha_file(ROOT / "data" / "spotify_reviews_18months.csv"),
                   "rows": 660622},
        "scope": {"method": "seeded shuffle of distinct texts (seed a5-scope-v1) + all golden-50 texts, until 100,000 IDs",
                  "distinct_texts": 66079, "review_ids": 100000},
        "roles": {
            "enrich": {"model": labels.JEV_MODEL, "prompt_version": labels.PROMPT_VERSION, "schema": labels.SCHEMA_VERSION,
                       "batch": "1 text per request", "workers": 4, "max_rps": enrich.JEV_MAX_RPS,
                       "questions": "pipeline/labels.py"},
            "advisor": {"model": enrich.ADVISOR_MODEL, "effort": "low", "threshold": enrich.ADVISOR_THRESHOLD,
                        "max_fraction": enrich.ADVISOR_MAX_FRACTION, "batch": enrich.ADVISOR_BATCH,
                        "prompt": "pipeline/enrich.py ADVISOR_SYSTEM"},
            "verify": {"model": verify.VERIFY_MODEL, "config": verify.VERIFY_CONFIG, "thinking": "disabled", "effort": "low",
                       "sample": 1000, "batch": verify.BATCH, "prompt": "pipeline/verify.py SYSTEM"},
            "group": {"model": downstream.GROUP_MODEL, "config": downstream.GROUP_CONFIG, "thinking": "disabled"},
            "memo": {"model": downstream.MEMO_MODEL, "config": downstream.MEMO_CONFIG, "effort": "low",
                     "prompt": "pipeline/downstream.py MEMO_SYSTEM"},
        },
        "label_config": enrich.LABEL_CONFIG,
        "budget_usd": 5.00,
        "outputs_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    }
    out = args.run_dir / "run_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
