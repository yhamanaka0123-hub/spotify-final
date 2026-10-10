"""Load processed outputs into the dashboard database (Neon Postgres). No model calls.

    .venv/bin/python -m pipeline.load_db --db work/full.db --run-dir runs/full

Tables: run_summary, issues, claims, reviews (every completed record with its source fields),
quarantine_summary, topic_month, memo, evaluation. Reloading replaces the previous load.
"""
import argparse
import csv
import json
import os
import sqlite3
from pathlib import Path

import psycopg

from pipeline.enrich import LABEL_CONFIG
from pipeline.runtime import load_env

SCHEMA = """
DROP TABLE IF EXISTS run_summary, issues, claims, reviews, quarantine_summary, topic_month, memo, evaluation;
CREATE TABLE run_summary (key TEXT PRIMARY KEY, value JSONB NOT NULL);
CREATE TABLE issues (issue_id TEXT PRIMARY KEY, rank INT, name TEXT, summary TEXT, complaint_count INT,
                     severity_sum INT, mean_severity NUMERIC(10,6), priority_score INT);
CREATE TABLE claims (claim_id TEXT PRIMARY KEY, issue_id TEXT, metric TEXT, value TEXT);
CREATE TABLE reviews (review_id TEXT PRIMARY KEY, review_text TEXT, review_rating INT, review_timestamp TEXT,
                      app_version TEXT, topic TEXT, intent TEXT, severity INT, sentiment REAL, needs_review BOOLEAN,
                      evidence_quote TEXT, entities JSONB, cache_source_id TEXT, issue_id TEXT, decided_by TEXT);
CREATE INDEX reviews_issue ON reviews(issue_id, severity DESC);
CREATE INDEX reviews_topic ON reviews(topic, intent);
CREATE TABLE quarantine_summary (reason TEXT PRIMARY KEY, n INT);
CREATE TABLE topic_month (month TEXT, topic TEXT, intent TEXT, n INT, severity_sum INT);
CREATE TABLE memo (id INT PRIMARY KEY, recommended_issue_id TEXT, markdown TEXT, check_problems JSONB);
CREATE TABLE evaluation (key TEXT PRIMARY KEY, value JSONB);
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True)
    ap.add_argument("--run-dir", required=True, type=Path)
    args = ap.parse_args()
    load_env()
    out = args.run_dir / "out"
    lite = sqlite3.connect(args.db)
    issue_of = {r["review_id"]: r["issue_id"] for r in csv.DictReader(open(out / "membership.csv"))}
    ranking = list(csv.DictReader(open(out / "ranking.csv")))
    names = json.loads((out / "issues.json").read_text())["issues"] if (out / "issues.json").exists() else {}
    memo = json.loads((out / "memo.json").read_text())["memo"]
    problems = json.loads((out / "memo_check.json").read_text())["problems"]
    summary = json.loads((args.run_dir / "run_summary.json").read_text())

    src = {row[0]: row[1:] for row in lite.execute(
        "SELECT review_id, review_text, review_rating, review_timestamp, app_version FROM reviews")}
    decided = dict(lite.execute("""SELECT rv.review_id, r.decided_by FROM reviews rv JOIN results r
                                   ON r.text_key = rv.text_key AND r.label_config = ?""", (LABEL_CONFIG,)))
    reviews, quarantine, months = [], {}, {}
    for line in open(out / "records.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r["status"] != "completed":
            reason = r["reason"].split(":")[0]
            quarantine[reason] = quarantine.get(reason, 0) + 1
            continue
        text, rating, ts, ver = src[r["review_id"]]
        reviews.append((r["review_id"], text, int(rating), ts, ver, r["topic"], r["intent"], r["severity"],
                        r["sentiment"], r["needs_review"], r["evidence_quote"], json.dumps(r["entities"]),
                        r.get("cache_source_id"), issue_of.get(r["review_id"]), decided.get(r["review_id"])))
        k = (ts[:7], r["topic"], r["intent"])
        n, s = months.get(k, (0, 0))
        months[k] = (n + 1, s + r["severity"])

    with psycopg.connect(os.environ["DATABASE_URL"]) as pg:
        pg.execute(SCHEMA)
        with pg.cursor() as cur:
            with cur.copy("COPY reviews FROM STDIN") as cp:
                for row in reviews:
                    cp.write_row(row)
            cur.executemany("INSERT INTO issues VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                            [(r["issue_id"], int(r["rank"]), names.get(r["issue_id"], {}).get("name"),
                              names.get(r["issue_id"], {}).get("summary"), int(r["complaint_count"]),
                              int(r["severity_sum"]), r["mean_severity"], int(r["priority_score"])) for r in ranking])
            cur.executemany("INSERT INTO claims VALUES (%s,%s,%s,%s)",
                            [(c["claim_id"], c["issue_id"], c["metric"], c["value"])
                             for c in csv.DictReader(open(out / "claims.csv"))])
            cur.executemany("INSERT INTO quarantine_summary VALUES (%s,%s)", list(quarantine.items()))
            cur.executemany("INSERT INTO topic_month VALUES (%s,%s,%s,%s,%s)",
                            [(m, t, i, n, s) for (m, t, i), (n, s) in months.items()])
            cur.execute("INSERT INTO memo VALUES (1,%s,%s,%s)",
                        (memo["recommended_issue_id"], memo["memo_markdown"], json.dumps(problems)))
            calls = [json.loads(l) for l in open(args.run_dir / "calls.jsonl")]
            cost = {}
            for c in calls:
                k = f"{c['role']}{'/advisor' if c.get('advisor') else ''}:{c['model']}"
                d = cost.setdefault(k, {"calls": 0, "failed": 0, "input_tokens": 0, "output_tokens": 0, "usd": 0.0})
                d["calls"] += 1
                d["failed"] += c["outcome"] == "failed"
                d["input_tokens"] += c["input_tokens"] or 0
                d["output_tokens"] += c["output_tokens"] or 0
                d["usd"] += c.get("cost_usd") or 0
            for key, value in (("counts", summary.get("counts")), ("label_config", LABEL_CONFIG),
                               ("cost_by_stage", cost), ("stage_seconds", summary.get("stage_seconds")),
                               ("total_rows", 660622)):
                cur.execute("INSERT INTO run_summary VALUES (%s,%s)", (key, json.dumps(value)))
            for name in ("verify_report.json",):
                p = args.run_dir / name
                if p.exists():
                    v = json.loads(p.read_text())
                    cur.execute("INSERT INTO evaluation VALUES (%s,%s)",
                                ("verify", json.dumps({k: v[k] for k in ("sampled", "verified", "agreement")})))
            g = Path("evals/golden_report.json")
            if g.exists():
                cur.execute("INSERT INTO evaluation VALUES (%s,%s)", ("golden", g.read_text()))
        pg.commit()
    print(f"loaded {len(reviews)} completed reviews, {len(ranking)} issues, quarantine {quarantine}")


if __name__ == "__main__":
    main()
