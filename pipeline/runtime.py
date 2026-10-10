"""Run bookkeeping shared by all stages: call log, spend ledger with reservations, rates.

Every model attempt (succeeded or failed) is appended to <run_dir>/calls.jsonl. The ledger
reserves an estimated worst-case cost before each dispatch and refuses new work once
spent + reserved + next reservation would exceed the budget.
"""
import csv
import json
import os
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RATES_CSV = ROOT / "cost" / "rates.csv"


def load_env():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")


def load_rates(path=RATES_CSV):
    rates = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rates[(row["model"], row["item"])] = float(row["price_usd_per_unit"])
    return rates


def cost_of(rates, model, input_tokens, output_tokens):
    if input_tokens is None:
        return None  # usage unavailable: leave unresolved rather than invent zero
    return (input_tokens * rates[(model, "input_tokens")]
            + (output_tokens or 0) * rates[(model, "output_tokens")])


class BudgetExceeded(Exception):
    pass


class Run:
    def __init__(self, run_dir, budget_usd, phase="initial"):
        self.dir = Path(run_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.calls_path = self.dir / "calls.jsonl"
        self.budget = budget_usd
        self.phase = phase
        self.rates = load_rates()
        self.lock = threading.Lock()
        self.reserved = 0.0
        self.spent = 0.0
        if self.calls_path.exists():  # resume: previous spend still counts against the cap
            with open(self.calls_path, encoding="utf-8") as f:
                for line in f:
                    self.spent += json.loads(line).get("cost_usd") or 0.0

    def reserve(self, amount):
        with self.lock:
            if self.spent + self.reserved + amount > self.budget:
                raise BudgetExceeded(
                    f"spent ${self.spent:.4f} + reserved ${self.reserved:.4f} + next ${amount:.4f} "
                    f"> budget ${self.budget:.2f}")
            self.reserved += amount

    def settle(self, reserved, actual):
        with self.lock:
            self.reserved -= reserved
            self.spent += actual or 0.0

    def log_call(self, *, role, model, review_ids, outcome, label_config, input_tokens, output_tokens,
                 started, request_id=None, error=None, **extra):
        rec = {
            "request_id": request_id or f"local-{uuid.uuid4()}",
            "role": role, "review_ids": list(review_ids), "model": model, "phase": self.phase,
            "outcome": outcome, "label_config": label_config,
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "cost_usd": cost_of(self.rates, model, input_tokens, output_tokens),
            "started_at": started, "duration_s": round(time.time() - started, 3), "pid": os.getpid(),
        }
        if error:
            rec["error"] = str(error)[:300]
        rec.update(extra)
        with self.lock, open(self.calls_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec
