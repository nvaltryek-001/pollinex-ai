# POLLINEX AI — Project Completion Report

_Date: 2026-11-03 · Repository: <https://github.com/nvaltryek-001/pollinex-ai> (branch `main`)._
_Verification: GitHub Actions runs #41626877962 and #41628075012 (all jobs green) plus the workspace's own engine tests._

## 1. Status in one paragraph
POLLINEX AI is **built, started and tested**: the FastAPI backend starts against PostgreSQL 16 and SQLite, migrations apply,
the React production build succeeds, and 37 engine, 24 backend, 11 frontend-unit and 14 browser end-to-end tests pass on clean
Ubuntu runners. The Windows setup and test scripts were run on a fresh Windows runner, and Docker Compose was smoke-tested.
Genuine screenshots come from those runs. Open items need resources this project does not have yet: labelled data, a GPU run,
hosting credentials and a real phone.

## 2. Features completed (implemented and exercised by automated tests)
| Area | What works |
|---|---|
| Auth & roles | register/login/logout (token revocation), PBKDF2 passwords, JWT, admin / researcher / user, admin user management, audit log, rate limiting |
| Scanner | upload (validated, EXIF-stripped), laptop/phone camera with permission handling and camera switching, capture & analyse, sampled live inference over WebSocket with HTTP fallback, detection overlays, history |
| Flower detection | trained CPU detector (boxes, scores, counts, low-confidence flags), close-up fallback clearly labelled; YOLO11 ONNX backend auto-used if trained |
| Species | open-set gallery returns `unknown` when unsure; **manual correction** keeps the original prediction and re-runs readiness; researchers add references per species |
| Stage / structures / health / pose | labelled heuristics; per-structure status table (anther, stigma, stamen, pistil = **not AI-validated**) |
| Readiness | species-specific rule engine (9 crops, distinct mechanisms), evidence, confidence, uncertainty, environment factors incl. missing/stale-data warnings |
| Simulator | seeded particle model, 6 species modes, Three.js scene with species structures, trails, play/pause/replay, timeline, speed, sweeps, 2-D fallback, persistence; disclaimer everywhere |
| Environment | manual records, Open-Meteo fetch with conditions, source and timestamp, trends, species assessment |
| Field records | fields, plants (inventory), pollination logs with observed outcomes |
| Analytics & reports | dashboard and analytics from DB records, model performance from saved evaluation reports, PDF/CSV/JSON downloads |
| Research & data | research centre (refs with links, documents), dataset management page (manifest, licences, audit) |
| Admin | users/roles, health, model registry + reload, evaluation runs, activity log |
| UI | 20 pages, sidebar + mobile navigation, light/dark theme, loading/empty/error states, toasts, provenance badges |
| Ops | Docker Compose (PostgreSQL + API + nginx), Render/Vercel configs, CI on Ubuntu + Windows, CI-resolved lock files, dependency checker, Windows scripts |

## 3. Test results
See `TESTING_REPORT.md`. Totals: **37 + 24 + 11 + 14 = 86 automated tests passing**, plus type-check, lint, production build,
migrations (SQLite up/down/up, PostgreSQL), backend startup (Linux + Windows), Docker builds and Compose smoke test.

| Check | Status |
|---|---|
| Frontend production build | ✅ (Ubuntu + Windows) |
| Backend startup | ✅ production mode on PostgreSQL (Ubuntu); development mode on SQLite (Windows) |
| Database | ✅ Alembic 0001→0002 on PostgreSQL 16 and SQLite; 20 tables |
| Docker | ✅ images build; Compose stack healthy |
| Windows scripts | ✅ setup + `test_windows.ps1 -E2E` (7/7 steps) + startup on windows-latest |

## 4. AI model status (actual, unchanged results)
| Model | Test-split result (held out, used once) | Source |
|---|---|---|
| CPU flower detector (deployed config 1280 px, stride 2) | mAP@0.5 **0.410**, mAP@0.5:0.95 **0.191**, P 0.169, R 0.610 | `ai-engine/reports/detector_inference_tradeoff.json` (session-1 run, 2026-11-02) |
| Baseline (Otsu) / colour-only ablation | mAP@0.5 0.127 / 0.240 | `detector_evaluation.json` |
| Species gallery (apple/peach/pear + unknown) | open-set acc 0.819, macro-F1 0.799, background rejection 0.468 | `species_evaluation.json` |
| YOLO11 | **not trained** (recipe + Colab guide provided) | — |
| Anther/stigma detector | **does not exist** (no labelled data) | — |
No metric was re-estimated or improved in this session.

## 5. Deployment status
* **Local**: fully usable (Windows scripts, bash scripts, Docker Compose) — verified in CI.
* **Public cloud**: **not deployed** (no hosting credentials in this project). Render + Vercel configurations are ready
  (`deployment/render.yaml`, `frontend/vercel.json`, `docs/DEPLOYMENT_GUIDE.md`). Free tiers sleep when idle and have ~512 MB RAM.

## 6. Remaining limitations
1. Detector trained on 3 orchard species only; precision is low on cluttered scenes; 6 crops have no evaluated species references.
2. No trained stage or reproductive-structure model (no labelled data) — heuristics, clearly labelled.
3. Readiness rules and simulation parameters are not biologically validated (field-trial design in `research/methodology.md`).
4. Camera verified with Chromium's fake device and a phone emulation profile, not on physical phones in CI.
5. No public deployment URL.
6. Rate limiter is per-process (use a proxy limiter for multi-worker deployments).

## 7. Honest completion
All software features in the original plan are implemented, integrated, built and automatically tested. What remains needs
external resources: data collection/annotation, a GPU training run, hosting accounts, and a manual check on a physical phone.
**This is not "100 %" of the research vision**; it is a complete, verified software platform whose scientific limits are
stated explicitly.

## 8. Run it on Windows
```powershell
git clone https://github.com/nvaltryek-001/pollinex-ai.git
cd pollinex-ai
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
powershell -ExecutionPolicy Bypass -File scripts\run_windows.ps1        # http://localhost:5173 (API docs: http://localhost:8000/docs)
powershell -ExecutionPolicy Bypass -File scripts\test_windows.ps1 -E2E  # optional: full test suite incl. Playwright
```
Requirements: Python 3.12 (python.org, "Add to PATH"), Node.js 20+ LTS, Git. Register the first account — it becomes admin.
For the phone camera, expose the dev server over HTTPS (e.g. `cloudflared tunnel --url http://localhost:5173`).
