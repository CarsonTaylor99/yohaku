#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "[setup] No .venv found. Run once:"
  echo "    python3 -m venv .venv"
  echo "    .venv/bin/pip install -r requirements.txt"
  echo "    cp .env.example .env"
  echo "    cp config/bindings.example.json config/bindings.json"
  echo "Then edit .env and add your API keys."
  exit 1
fi

if [ ! -f .env ]; then
  echo "[setup] .env not found. Run: cp .env.example .env"
  echo "Then open .env and fill in your API keys."
  exit 1
fi

echo "yohaku -> http://127.0.0.1:8000  (Ctrl+C to stop)"
exec .venv/bin/uvicorn backend.main:app --reload
