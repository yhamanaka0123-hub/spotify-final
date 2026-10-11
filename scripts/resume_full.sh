#!/usr/bin/env bash
# Resume the full run after the checkpoint. Completed texts are never re-sent (same label_config).
cd "$(dirname "$0")/.." || exit 1
.venv/bin/python -u -m pipeline.run --input data/spotify_reviews_18months.csv --db work/full.db \
  --run-dir runs/full --budget 5.00 --verify-sample 1000 --workers 4 --phase resume 2>&1 | tee -i -a runs/full/resume_console.log
