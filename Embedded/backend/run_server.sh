#!/bin/bash
cd "$(dirname "$0")"

# Use Python 3.12 from conda base (already has uvicorn installed)
PYTHON_BIN="$HOME/miniconda3/bin/python3.12"
exec "$PYTHON_BIN" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
