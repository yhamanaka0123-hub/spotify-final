"""Shared definitions from GRADING_CONTRACT.md, reusing the course checker's helpers
so row hashes and CSV parsing match the grader byte-for-byte."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("check_submission", ROOT / "data" / "check_submission.py")
_checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_checker)

FIELDS = _checker.FIELDS
TOPICS = _checker.TOPICS
INTENTS = ("cancellation", "complaint", "request", "praise", "unclear")  # precedence order
csv_rows = _checker.csv_rows
row_sha = _checker.row_sha
sha_file = _checker.sha
