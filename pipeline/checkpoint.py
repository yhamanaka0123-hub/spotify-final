"""Snapshot completed review IDs (for checkpoint_before.json / checkpoint_after.json). No model calls.

    .venv/bin/python -m pipeline.checkpoint --db work/full.db --out grading/checkpoint_before.json
"""
import argparse
import json
import sqlite3
import time
from pathlib import Path

from pipeline.enrich import LABEL_CONFIG


def completed_ids(con):
    return [rid for (rid,) in con.execute("""
        SELECT rv.review_id FROM reviews rv JOIN results r
          ON r.text_key = rv.text_key AND r.label_config = ?
        ORDER BY rv.row_num""", (LABEL_CONFIG,))]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    con = sqlite3.connect(args.db)
    ids = completed_ids(con)
    texts = con.execute("SELECT COUNT(*) FROM results WHERE label_config=?", (LABEL_CONFIG,)).fetchone()[0]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"label_config": LABEL_CONFIG, "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                    "completed_texts": texts, "completed_count": len(ids),
                                    "completed_ids": ids}) + "\n", encoding="utf-8")
    print(f"{args.out}: {len(ids)} completed review IDs from {texts} classified texts")


if __name__ == "__main__":
    main()
