"""Stage 1 - Prepare: ingest any review CSV into SQLite. No model calls.

    .venv/bin/python -m pipeline.prepare --input data/cost_100.csv --db work/cost_100.db

- Reads every row with a multiline-safe CSV parser (the course checker's reader).
- Preserves the six source strings exactly and stores the contract row hash.
- Groups rows by exact text so each distinct text is classified once (cache key).
- Quarantines empty texts with reason `empty_review_text`.
- Writes an ingestion report next to the database.
"""
import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from pipeline.contract import FIELDS, csv_rows, row_sha, sha_file

SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    row_num INTEGER NOT NULL,
    review_text TEXT NOT NULL,
    review_rating TEXT NOT NULL,
    review_likes TEXT NOT NULL,
    app_version TEXT NOT NULL,
    review_timestamp TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    text_key TEXT,               -- sha256 of exact text; NULL for empty text
    status TEXT NOT NULL,        -- pending | completed | quarantined
    reason TEXT
);
CREATE INDEX IF NOT EXISTS reviews_text_key ON reviews(text_key);
CREATE TABLE IF NOT EXISTS texts (
    text_key TEXT PRIMARY KEY,
    review_text TEXT NOT NULL,
    n_rows INTEGER NOT NULL,
    first_review_id TEXT NOT NULL  -- the original record that carries model-call evidence
);
"""


def text_key(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ingest(input_csv, db_path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    counts = Counter(records=0, duplicate_review_ids=0, empty_review_text=0, missing_app_version=0)
    ratings, months = Counter(), Counter()
    seen = set()
    rows = []
    for i, row in enumerate(csv_rows(input_csv)):
        rid = row["review_id"]
        counts["records"] += 1
        if rid in seen:
            counts["duplicate_review_ids"] += 1
            continue
        seen.add(rid)
        empty = not row["review_text"].strip()
        counts["empty_review_text"] += empty
        counts["missing_app_version"] += not row["app_version"].strip()
        ratings[row["review_rating"]] += 1
        months[row["review_timestamp"][:7]] += 1
        rows.append((rid, i, *(row[k] for k in FIELDS[1:]), row_sha(row),
                     None if empty else text_key(row["review_text"]),
                     "quarantined" if empty else "pending",
                     "empty_review_text" if empty else None))
    con.executemany("INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.execute("""
        INSERT INTO texts
        SELECT text_key, review_text, COUNT(*),
               (SELECT r2.review_id FROM reviews r2 WHERE r2.text_key = r.text_key ORDER BY r2.row_num LIMIT 1)
        FROM reviews r WHERE text_key IS NOT NULL GROUP BY text_key
    """)
    con.commit()
    distinct = con.execute("SELECT COUNT(*) FROM texts").fetchone()[0]
    nonempty = counts["records"] - counts["duplicate_review_ids"] - counts["empty_review_text"]
    report = {
        "input": str(input_csv),
        "file_sha256": sha_file(input_csv),
        "file_bytes": input_csv.stat().st_size,
        "counts": dict(counts),
        "nonempty_reviews": nonempty,
        "distinct_nonempty_texts": distinct,
        "rows_reusing_exact_text": nonempty - distinct,
        "reviews_by_rating": dict(sorted(ratings.items())),
        "reviews_by_month": dict(sorted(months.items())),
        "quarantined": {"empty_review_text": counts["empty_review_text"]},
    }
    con.close()
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--db", required=True, type=Path)
    args = ap.parse_args()
    report = ingest(args.input, args.db)
    out = args.db.with_suffix(".ingestion_report.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("counts", "nonempty_reviews", "distinct_nonempty_texts")}, indent=2))
    print("wrote", out)


if __name__ == "__main__":
    main()
