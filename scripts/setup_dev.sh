#!/usr/bin/env bash
# One-time local setup (Linux/macOS; on Windows use Git Bash or WSL). Requires Python 3.11+ and Node 20+.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

[ -f .env ] || { cp .env.example .env; echo "Created .env - edit JWT_SECRET before production use."; }

(cd frontend && npm install --no-audit --no-fund)
echo "Setup complete. Start with: scripts/run_dev.sh"
