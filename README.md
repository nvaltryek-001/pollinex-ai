# POLLINEX AI

### Intelligent multi-species flower analysis, pollination-readiness estimation and virtual pollination simulation

[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2ea44f)](.github/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-3776ab) ![React](https://img.shields.io/badge/react-18-61dafb)
![Licence](https://img.shields.io/badge/code-MIT-blue) ![Data](https://img.shields.io/badge/training%20data-CC%20BY%204.0-orange)

POLLINEX AI is a **software-only** research platform that runs on a laptop and a phone browser. It detects flowers in photos and
live camera frames, recognises species with an **open-set** reference gallery, estimates visible developmental stage, inspects the
flower centre and visible health, and turns **species-specific pollination biology** into explainable, uncertainty-aware
recommendations. A **Three.js simulator** replays seeded particle simulations of pollen transfer.

> **Honesty first.** Every output in the API, UI and reports is tagged with how it was produced —
> `trained_model`, `trained_reference_gallery`, `heuristic`, `rule_engine`, `simulation`, `closeup_fallback` or `user_declared`.
> Readiness is a *visual estimate*, simulated transfer is *not* fruit set, and no metric shown anywhere is a placeholder.

---

## Contents
1. [What was built](#what-was-built) · 2. [Measured results](#measured-results) · 3. [Architecture](#architecture) ·
4. [Tech stack](#technology-stack) · 5. [Quick start](#quick-start) · 6. [Usage](#usage) · 7. [API](#api) ·
8. [Datasets & credits](#datasets--credits) · 9. [Research](#research) · 10. [Limitations](#limitations-read-this) ·
11. [Project audit](#project-audit) · 12. [Repository layout](#repository-layout)

## What was built

| Area | What it does | Evidence type |
|---|---|---|
| **Flower detection** (Module 1) | Pixel classifier (gradient-boosted trees on a 36-channel colour/texture stack) → probability map → instances → boxes, scores, count, low-confidence warnings. Trained **in this repo** on CPU. Optional YOLO11 ONNX backend is auto-used when its file exists. | trained model |
| **Species recognition** (Module 2) | kNN reference gallery with an open-set threshold calibrated on validation; returns `unknown` instead of forcing a class; researchers can add reference images for new species without retraining. | trained reference gallery |
| **Flower centre / structures** (Module 3) | Locates the distinct centre region and pollen-like yellow cluster. **Does not detect anthers/stigma** (no licensed annotations exist) — CVAT workflow + training recipe provided. | heuristic |
| **Maturity stage** (Module 4) | Bud / early bloom / partially open / fully open / senescent from shape & colour cues. | heuristic |
| **Readiness intelligence** (Module 5 + Part 6) | Rule engine over a 9-species knowledge base (mechanism, compatibility, ready stages, env. ranges, evidence, limitations). Different strategies per crop: vibration (tomato, brinjal), compatible cross-pollen (apple, pear), brush/contact (chilli, peach, hibiscus), air-assisted (strawberry), ring progression (sunflower). | rule engine |
| **Pose & approach guidance** (Module 6) | Image-space centre, facing ratio, axis angle and alignment vector to a virtual effector (explicitly *not* metric). | heuristic |
| **Visual health** (Module 7) | Browning, dark spots, discolouration, outline irregularity — measurements only, never a disease name. | heuristic |
| **Evaluation** (Module 8) | COCO-style mAP@0.5 / 0.5:0.95, P/R/F1, per-species, AP-vs-IoU, count error, pixel IoU, latency, confusion matrix, leave-one-species-out, error analysis. | measured |
| **Live scanner** | Upload, phone/laptop camera (permission handling, camera switching), capture & analyse, **sampled** live inference over WebSocket (HTTP fallback) with back-pressure and an adjustable interval. | — |
| **Virtual simulator** | Seeded 3-D particle model per species profile; Three.js replay with orbit, scrubbing, replay; 2-D canvas fallback; sensitivity sweeps (alignment, wind, vibration Hz). | simulation |
| **Environment** | Manual records + Open-Meteo fetch (source + timestamp stored; explicit error if unavailable — never invented). | — |
| **Web app** | 20 pages: landing, auth, dashboard, scanner, species, structure, maturity, readiness, simulator, environment, health, fields, inventory, pollination history, model evaluation, analytics, research centre, reports, datasets, admin. Dark/light themes, mobile-first. | — |
| **Platform** | FastAPI + SQLAlchemy 2 + Alembic, JWT auth with admin / researcher / user roles, token revocation on logout, PBKDF2 passwords, upload validation (type, size, decompression bombs, EXIF/GPS stripping), CSV/PDF/JSON reports, audit log, Docker Compose (PostgreSQL), CI workflow. | — |

## Measured results

All numbers come from `ai-engine/reports/*.json`, produced by the training scripts on a **held-out test split that was used once**
(parameters chosen on validation). Hardware: 2 vCPU cloud VM, no GPU.

**Data:** USDA Multi-species Fruit Flower dataset (apple, peach, pear) — 90 usable images, 4,651 mask-derived instances,
group-aware contiguous splits **54 / 14 / 22** images, 0 near-duplicates across splits.

### Flower detector — baseline & ablation (test split, same protocol)

| Variant | val mAP50 | **test mAP50** | test mAP50-95 | Precision | Recall | Pixel IoU | ms / image* |
|---|---|---|---|---|---|---|---|
| A · Otsu "whiteness" threshold (no learning) | 0.110 | 0.127 | 0.062 | 0.046 | 0.451 | 0.072 | 11 |
| B · boosted trees, 12 colour features | 0.276 | 0.240 | 0.109 | 0.059 | 0.593 | 0.149 | 4,664 |
| C · boosted trees, full 36 features | 0.491 | 0.405 | 0.186 | 0.167 | 0.626 | 0.371 | 9,569 |
| **C · deployed config (1280 px, stride 2)** | **0.506** | **0.410** | **0.191** | 0.169 | 0.610 | — | **1,990** |
| C · live-scan config (800 px, stride 2) | 0.384 | 0.305 | 0.129 | 0.215 | 0.439 | — | 676 |

\*per image on the 2-vCPU build machine. Configs were selected on **validation** with rules fixed beforehand.
Per-species test mAP50: apple 0.395 · peach 0.491 · pear 0.420 (stride-1 run). Recall rises with object size
(small < 16 px: 0.47 · medium: 0.64 · large > 40 px: 0.75).

**Interpretation:** a modest CPU baseline, far below deep detectors reported in the literature (we make no comparison claim).
Precision is low because pale bark and unlabelled background blossoms produce false positives (see the error analysis and
`ai-engine/reports/figures/`). The YOLO11 recipe is included to replace it once PyTorch is available.

### Species gallery (open-set, test split)

| Metric | Value |
|---|---|
| Open-set accuracy over {apple, peach, pear, unknown} | 0.819 (macro-F1 0.799) |
| Accuracy on flower crops only | 0.931 |
| Background crops rejected as `unknown` | 0.468 |
| Leave-one-species-out → returned `unknown` | apple 0.435 · peach 0.919 · pear 0.219 |

**Caveat:** each species in this dataset comes from a different camera setup, so species is confounded with capture conditions.
These numbers validate the *mechanism* (gallery + open-set rejection), not field-general species recognition. The other six
target crops have no evaluated references yet and return `unknown` unless the user declares the species or researchers add references.

### What was *not* measured
Stage, centre-region, health and pose heuristics (no labels exist), readiness rules (no biological ground truth), the
simulator (no physical trial), YOLO11 (not trainable in the build environment), and anything about fertilisation or yield.

## Architecture

```mermaid
flowchart LR
  subgraph Browser["React + Vite PWA (phone / laptop)"]
    UI[20 pages · Tailwind · Recharts]
    CAM[Camera API<br/>frame sampler]
    SIM3D[Three.js replay<br/>+ 2D fallback]
  end
  subgraph API["FastAPI (Python)"]
    AUTH[JWT auth · roles]
    SCAN[/scans · live WS/]
    AI[/ai/*/]
    SIMR[/simulations/]
    REC[/fields · plants · env · logs/]
    AN[/analytics · reports/]
  end
  subgraph Engine["ai-engine (pure Python, CPU)"]
    DET[Detector<br/>pixel-HGB or YOLO11-ONNX]
    GAL[Open-set species gallery]
    HEU[Stage · centre · health · pose heuristics]
    KB[(Species knowledge base)]
    RUL[Readiness rule engine]
  end
  SIMP[simulation<br/>seeded particle model]
  DB[(PostgreSQL / SQLite)]
  FS[(Image storage<br/>sha256, EXIF stripped)]
  OM[(Open-Meteo<br/>optional)]

  UI -- REST --> API
  CAM -- WebSocket / HTTP --> SCAN
  SIM3D -- replay frames --> SIMR
  SCAN --> DET --> GAL --> HEU --> RUL
  RUL --> KB
  SIMR --> SIMP
  API --> DB
  SCAN --> FS
  REC --> OM
```

More detail: [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) · [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md).

## Technology stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 18, Vite 5, TypeScript, Tailwind 3, Recharts, Three.js, lucide-react | Spec stack; small bundle; mobile-first |
| Backend | FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, PyJWT, WebSocket | Typed REST + OpenAPI docs + live channel |
| AI runtime | NumPy, SciPy, OpenCV, scikit-learn, scikit-image, onnxruntime (optional) | **No PyTorch needed to run** → works on any laptop CPU |
| AI training (optional) | Ultralytics YOLO11 + PyTorch → ONNX | Deep detector path (AGPL-3.0, see docs) |
| Database | PostgreSQL 16 (Docker/prod), SQLite (local dev) | Zero-setup dev, real DB in prod |
| Reports | ReportLab (PDF), CSV, JSON | Offline |
| Tests | Pytest, Vitest + Testing Library, Playwright | Unit → E2E |
| Deploy | Docker, Docker Compose, Render blueprint, Vercel config, GitHub Actions | |

## Quick start

**Requirements:** Python 3.11+, Node 20+ (or Docker). No GPU, no paid API.

### Option A — local development
```bash
git clone https://github.com/<you>/pollinex-ai.git && cd pollinex-ai
scripts/setup_dev.sh          # venv + pip install + npm install + .env
scripts/run_dev.sh            # API on :8000, web app on :5173
```
Open http://localhost:5173, register (the **first account becomes admin**), and open the **Flower scanner**.
Try `tests/fixtures/sample_orchard.jpg` (a CC-BY test image from the dataset).
Swagger UI: http://localhost:8000/docs

Windows (PowerShell): `python -m venv .venv; .venv\Scripts\activate; pip install -r backend\requirements.txt`, then
`cd backend; uvicorn app.main:app --reload` and in another terminal `cd frontend; npm install; npm run dev`.

### Option B — Docker Compose (PostgreSQL)
```bash
cp .env.example .env     # set POSTGRES_PASSWORD and JWT_SECRET
docker compose up --build
# web: http://localhost:8080   api docs: http://localhost:8000/docs
```

### Using the phone camera
Browsers only allow the camera on **HTTPS** or `localhost`. On a LAN, serve the frontend over HTTPS (e.g. `mkcert` +
Vite `server.https`, or a tunnel such as `cloudflared`), or deploy (Vercel + Render). Image upload works everywhere,
and on phones the upload button can open the camera directly. Details: [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md).

### Reproduce the models
```bash
SRC=/path/to/clone/of/multi-species-fruit-flower scripts/reproduce_models.sh
```

## Usage

1. **Scan** — upload or use the camera. Choose *auto* (orchard scene, falls back to close-up if nothing confident is found),
   *scene* or *close-up*; optionally declare the species, link a plant and an environment record.
2. **Read the result** — boxes over the image (solid = confident, dashed amber = low confidence, dashed red = close-up
   fallback), then per-flower species, stage, centre, health, pose and the readiness card with strategy, observations,
   uncertainty, limitations and sources.
3. **Simulate** — open the simulator from a readiness card; adjust alignment, wind, vibration frequency; compare runs.
4. **Record** — log real pollination actions and their observed outcome; add fields, plants and weather records.
5. **Analyse & export** — dashboard, analytics (admins/researchers can see all accounts), PDF / CSV / JSON reports.

## API

Interactive OpenAPI docs at `/docs`. Main groups (all under `/api/v1`):

| Group | Endpoints |
|---|---|
| Auth | `POST /auth/register` · `POST /auth/login` · `POST /auth/logout` · `GET /auth/me` |
| Scanning | `POST /scans` (upload + analyse) · `GET /scans` · `GET /scans/{id}` · `GET /scans/{id}/image` · `DELETE /scans/{id}` · `POST /scans/live/frame` · `WS /scans/live/ws` |
| AI modules | `POST /ai/detect` · `/ai/analyze` · `/ai/classify-species` · `/ai/structure` · `/ai/maturity` · `/ai/health` · `/ai/readiness` · `GET /ai/species` · `POST /ai/species/{id}/references` |
| Simulation | `POST /simulations` · `POST /simulations/{id}/execute` · `GET /simulations/{id}` · `GET /simulations/{id}/replay` · `POST /simulations/sweep` |
| Records | `/fields` · `/plants` · `/environment` · `POST /environment/fetch` · `/environment/{id}/assessment` · `/pollination-records` |
| Analytics & reports | `GET /analytics/dashboard` · `/analytics/species` · `/analytics/model-performance` · `/reports/scans.csv` · `/reports/summary.pdf` · `/reports/scans/{id}.json` |
| Admin | `/admin/users` · `/admin/activity` · `/admin/models` · `POST /admin/models/reload` · `/datasets` · `/research/references` · `/health` |

Full reference: [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md).

## Datasets & credits

| Dataset | Status | Licence | Use |
|---|---|---|---|
| **Multi-species Fruit Flower** — Dias, Tabb & Medeiros (2018), USDA Ag Data Commons, doi:10.15482/USDA.ADC/1423466 | **integrated** | CC BY 4.0 | detector training/evaluation; species gallery |
| TensorFlow Flower Detection (INESC TEC, Zenodo 7768292) | script provided | CC BY 4.0 | future YOLO11 training on close-ups |
| Oxford 102 Flowers (Nilsback & Zisserman 2008) | script provided | terms unverified | species gallery only (sunflower, hibiscus) |
| FlowerNet (Mendeley 26nvt3t27m v2) | script provided (originals only) | MIT | hibiscus gallery; 5,600 augmented copies excluded to avoid leakage |
| EWD wildflowers · DoPI · FloPE · PlantCLEF | documented, not ingested | CC BY-NC / none / n.a. / unverified | methodology only (reasons in manifest) |

**Data audit finding:** the mirror's per-image bounding boxes are inconsistently oriented (often vertically flipped) relative to
the images and masks, so POLLINEX derives instances from the masks instead. See `datasets/reports/usda_fruit_flower_report.md`.
Full manifest: [`datasets/dataset_manifest.csv`](datasets/dataset_manifest.csv) · [`docs/DATASET_DOCUMENTATION.md`](docs/DATASET_DOCUMENTATION.md).
No image archives or large weights are committed — download scripts rebuild everything.

## Research

Literature review of FloPE (IROS 2025), Broussard et al. (Agronomy 2023), Zhang et al. (Comput. Electron. Agric. 2025),
Singh et al. (AI Review 2025), Schouten et al. (PLOS ONE 2024) and DoPI (Ecology 2022), plus the dataset paper and
detection/segmentation references. Five research gaps and how the software responds are documented in
[`research/`](research/) (`literature_review.md`, `research_comparison.md`, `research_gaps.md`, `methodology.md`, `references.bib`).
Our contributions are engineering contributions; no external paper's results are claimed as ours.

## Limitations (read this)

* **Detector** is trained only on apple/peach/pear orchard photos; it confuses pale bark with petals and misses many small
  flowers (test precision 0.17, recall 0.61). On close-ups of other crops the app falls back to whole-image analysis and says so.
* **Species** evaluation is confounded with camera setup; six of nine crops have no evaluated references.
* **No anther/stigma detection.** Structure, stage, health and pose are heuristics, not trained models.
* **Readiness** is a rule-based *visual* estimate from general horticultural knowledge; not validated against receptivity or fertilisation.
* **Simulation** models geometry and simple physics only; parameters (e.g. canopy wind attenuation 0.02, carry fraction 0.75) are assumptions.
* **Environment rules** are general ranges; verify locally.
* **Licensing:** Ultralytics YOLO11 is AGPL-3.0 — only relevant if you train/ship the optional deep detector.

## Project audit

Honest status as delivered from the build environment (2 vCPU, no GPU, PyPI/npm/Docker Hub **blocked**, only GitHub reachable):

| Item | Status |
|---|---|
| Research review, gaps, methodology, BibTeX | ✅ done (some volume/article numbers marked unverified) |
| Dataset manifest + licences + prep scripts | ✅ USDA set prepared & audited; other scripts written, not run (hosts blocked) |
| Detector trained & evaluated | ✅ real metrics above |
| Species gallery + open-set evaluation | ✅ (with confound caveat) |
| Stage / centre / health / pose modules | ✅ implemented as labelled heuristics · ⚠️ not accuracy-evaluated |
| Reproductive-structure detector | ❌ no training data — annotation workflow + recipe provided |
| YOLO11 deep detector | ⚠️ recipe + ONNX runtime path written; **not trained** (no PyTorch available) |
| Readiness engine + 9-species knowledge base | ✅ |
| Simulator engine + Three.js / 2D UI | ✅ engine tested · ⚠️ UI not run in a browser here |
| Backend API, DB models, migration, auth, reports | ✅ written · ✅ report generation executed · ⚠️ API test-suite (20 tests) written but **not executed** here (FastAPI/SQLAlchemy not installable) |
| Frontend (20 pages, scanner, camera, live WS) | ✅ written · ✅ syntax-checked · ⚠️ not built/type-checked against dependencies here (npm blocked) |
| Automated tests executed | ✅ **35/35** AI-engine + simulation tests pass |
| Docker images, deployment | ⚠️ files written; not built (no Docker daemon); no deployment URL |
| Screenshots | ❌ not possible without running the frontend — add after first local run |

**Honest completion estimate: ~70 %.** The research, data, AI and simulation core is complete and measured; the web stack is
fully written but its first build/test run must happen on a machine with package-registry access (`scripts/run_tests.sh`).
See [`docs/FINAL_PROJECT_REPORT.md`](docs/FINAL_PROJECT_REPORT.md) and [`docs/TESTING_REPORT.md`](docs/TESTING_REPORT.md).

## Repository layout

```
frontend/      React + Vite + TS app (pages/, components/, lib/, e2e/)
backend/       FastAPI app (routers/, services/, models.py), Alembic migrations, tests
ai-engine/     pollinex_ai package (detector, species, maturity, structure, health, pose, readiness, knowledge base),
               training/ scripts, models/ (small shipped models), reports/ (evaluation JSON + figures), tests
simulation/    pollinex_sim particle engine + tests
datasets/      manifest, sources, licences, prep/download scripts, annotation workflow, splits, COCO annotations, reports
research/      literature review, comparison, gaps, methodology, references (.bib/.json)
docs/          architecture, schema, API, models, datasets, methodology, install, deploy, testing, manual, final report
deployment/    Render blueprint (Vercel config lives in frontend/)
scripts/       setup / run / test / reproduce helpers
tests/         shared fixtures (CC BY test images)
```

## Licence

Code: MIT (see `LICENSE`). Training data and the fixture images: CC BY 4.0, © Dias, Tabb & Medeiros — please cite
doi:10.15482/USDA.ADC/1423466 and doi:10.1109/LRA.2018.2849498 if you use the trained models.
