#!/bin/bash
cd "$(dirname "$0")"

# Cloudinary credentials
export CLOUDINARY_URL="cloudinary://919668245813367:UEkNEm7d4cUChmbtxYAOXequn3A@dhhdd4pkl"
export CLOUDINARY_FOLDER="pcb-inspector"

# Use Python 3.12 from conda base (already has uvicorn installed)
PYTHON_BIN="$HOME/miniconda3/bin/python3.12"
exec "$PYTHON_BIN" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
