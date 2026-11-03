#!/usr/bin/env bash
# Runs every automated test suite. E2E (Playwright) needs the dev stack running: scripts/run_dev.sh
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
[ -d .venv ] && source .venv/bin/activate

echo "== AI engine + simulation"; python -m pytest -q ai-engine/tests simulation/tests
echo "== Backend";               python -m pytest -q backend/tests
echo "== Migrations";            (cd backend && DATABASE_URL="sqlite:///./_migration_check.db" alembic upgrade head && rm -f _migration_check.db)
echo "== Frontend";              (cd frontend && npm run typecheck && npm test && npm run build)
if [ "${E2E:-0}" = "1" ]; then
  echo "== E2E"; (cd frontend && npx playwright install chromium && npm run test:e2e)
fi
