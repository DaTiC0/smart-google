#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "[pre-pr] using python: $PYTHON_BIN"
echo "[pre-pr] installing local check tools (flake8, pytest, pylint) if needed"
"$PYTHON_BIN" -m pip install -q flake8 pytest pylint

echo "[pre-pr] check absolute paths"
bash scripts/check_absolute_paths.sh

echo "[pre-pr] flake8 hard-fail gate (syntax/errors)"
"$PYTHON_BIN" -m flake8 . \
  --exclude=.venv,venv,.git,__pycache__ \
  --count --select=E9,F63,F7,F82 --show-source --statistics

echo "[pre-pr] flake8 advisory gate (style/complexity, non-blocking)"
"$PYTHON_BIN" -m flake8 . \
  --exclude=.venv,venv,.git,__pycache__ \
  --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

echo "[pre-pr] pytest"
"$PYTHON_BIN" -m pytest -q

echo "[pre-pr] pylint error gate for DeepSource-like failures"
"$PYTHON_BIN" -m pylint my_oauth.py -E

echo "[pre-pr] all checks passed"
