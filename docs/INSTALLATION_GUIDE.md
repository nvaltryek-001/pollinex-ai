# Installation Guide

## Requirements
* Python **3.11+** (3.12 recommended), Node **20+**, Git. ~1 GB disk (more if you re-download the dataset: ~6 GB clone).
* 4 GB RAM is enough; no GPU.
* Optional: Docker + Docker Compose; PostgreSQL 14+.

## 1. Clone and configure
```bash
git clone https://github.com/<you>/pollinex-ai.git
cd pollinex-ai
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into JWT_SECRET
```

## 2. Backend
```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload        # http://localhost:8000/docs
```
Local dev uses SQLite (`backend/pollinex.db`) and creates tables automatically. For PostgreSQL set `DATABASE_URL` and run
`alembic upgrade head` with `AUTO_CREATE_TABLES=false`.

**scikit-learn version:** the shipped detector was saved with scikit-learn 1.9.1 (pinned). If your platform cannot install
that version, install the closest available one and retrain (≈ 30 min on 2 cores):
`python datasets/scripts/prepare_usda_fruit_flower.py && python ai-engine/training/train_detector.py && python ai-engine/training/evaluate_detector.py`.

## 3. Frontend
```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173 (proxies /api to :8000)
```

## 4. First login
Register — the first account becomes **admin**. Or set `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` before first start.

## 5. Verify
```bash
scripts/run_tests.sh                 # pytest (engine, simulation, API), alembic, typecheck, vitest, build
E2E=1 scripts/run_tests.sh           # + Playwright (stack must be running)
curl http://localhost:8000/api/v1/health
```

## Troubleshooting
| Symptom | Fix |
|---|---|
| `models: error ... different feature version` in /health | retrain the detector (see above) |
| Camera button errors on phone | needs HTTPS — see `USER_MANUAL.md` |
| `Weather provider unavailable` | Open-Meteo unreachable; enter observations manually |
| 401 after restart in dev | no `JWT_SECRET` set → ephemeral secret; set one in `.env` |
