#!/usr/bin/env bash
# Starts the FastAPI backend (port 8000) and the Vite dev server (port 5173, proxies /api).
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source .venv/bin/activate
set -a; [ -f .env ] && source .env; set +a

(cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT
cd frontend && npm run dev
