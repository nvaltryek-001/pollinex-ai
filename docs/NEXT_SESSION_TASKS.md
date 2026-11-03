# Next Session Tasks

_Updated 2026-11-03 (session 3). The build/test blocker is resolved: CI builds and tests everything on Ubuntu and Windows.
Remaining work needs external resources._

1. **Physical phone check** — run `scripts\run_windows.ps1`, expose it with `cloudflared tunnel --url http://localhost:5173`,
   open the HTTPS URL on Android Chrome / iOS Safari, test rear/front camera, live scan and capture.
2. **Public deployment** — Render blueprint (`deployment/render.yaml`) + Vercel (`frontend/`, `VITE_API_URL`); record URLs in README.
3. **YOLO11** — Colab guide in `docs/AI_MODEL_DOCUMENTATION.md`; report only measured test-split numbers.
4. **Data for the six crops without public data** (hibiscus, tomato, sunflower, strawberry, brinjal, chilli): collect, annotate with
   CVAT (`datasets/annotation/`), keep a held-out test set, add gallery references, evaluate.
5. **Structure / stage models** — once annotated, train and install as ONNX; flip the structure status from *not AI-validated*.
6. Optional: automated test for database-unavailable behaviour; HttpOnly-cookie sessions; proxy-level rate limiting.

Refresh screenshots/lock files: push a commit whose message contains `[publish]` (CI commits them back).

---
_Session-2 version (historical):_

# Next Session Tasks

_Written 2026-11-03 because package registries (PyPI, npm) and Docker Hub were blocked in the build environment.
Everything below is ordered; each step lists the exact command and what "done" means._

## 0. Prerequisite
Package access: either run on your own laptop (Windows instructions below) **or** in a Claude session where
`pypi.org`, `files.pythonhosted.org` and `registry.npmjs.org` are allowed (claude.ai → Settings → Capabilities; a **new**
session may be required for the change to apply).

## 1. Install & first run
Windows (PowerShell, repo root):
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
powershell -ExecutionPolicy Bypass -File scripts\run_windows.ps1
```
Linux/macOS: `scripts/setup_dev.sh && scripts/run_dev.sh`.
Done when `http://localhost:8000/api/v1/health` → `"status": "ok"` and `http://localhost:5173` shows the landing page.

## 2. Run every suite and fix failures
```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_windows.ps1        # pytest x2, alembic, typecheck, vitest, build
powershell -ExecutionPolicy Bypass -File scripts\test_windows.ps1 -E2E   # + Playwright
```
Expected first-run fixes (never executed before): TypeScript strictness errors, Recharts/Three typings, SQLAlchemy
pagination subquery with joined relationships, Playwright selectors. Fix the code, not the tests (unless a test is wrong).
Done when every line of the summary says PASS → record results in `docs/TESTING_REPORT.md` (name, status, result, failure, fix).

## 3. Manual checks
- Upload `tests/fixtures/sample_orchard.jpg` → boxes, species, stage, readiness; correct one species; confirm readiness changes.
- Camera on laptop (Chrome/Edge, `localhost`), then phone via HTTPS tunnel: `cloudflared tunnel --url http://localhost:5173`.
  Test rear/front switch, deny-permission message, live scan at 1.5 s interval.
- Simulator: each of the 6 modes in 3-D and 2-D; speed control; sweep.
- Environment: Open-Meteo fetch (shows conditions, source, retrieval time); manual record with missing fields → warning.
- Reports: PDF + CSV download. Admin: change a role; a standard user gets 403 on `/app/admin`.

## 4. Screenshots
Take PNGs of landing, dashboard, scanner results, simulator (3-D), evaluation page; save under `docs/screenshots/` and add to
README "Screenshots". Only genuine screenshots.

## 5. Docker
```bash
cp .env.example .env   # set POSTGRES_PASSWORD, JWT_SECRET
docker compose up --build
```
Done when `http://localhost:8080` works against PostgreSQL and migrations `0001`, `0002` applied.

## 6. Optional
- YOLO11 on Colab (`docs/AI_MODEL_DOCUMENTATION.md` → Colab section); report only measured numbers.
- Add references for the 6 un-evaluated crops with a held-out test folder; re-run `train_species.py --extra-gallery`.
- Deploy: Render blueprint (`deployment/render.yaml`) + Vercel (`frontend/`), then record URLs in README.

## 7. Push
```bash
git add -A && git status   # check no .env, no datasets/raw|processed, no *.pt/*.onnx > a few MB
git commit -m "Verification: all suites executed, fixes, screenshots"
git push origin main
```
