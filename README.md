<div align="center">

<img src="docs/assets/banner.svg" alt="POLLINEX AI — multi-species flower intelligence and virtual pollination" width="100%">

<br>

[![CI](https://github.com/nvaltryek-001/pollinex-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/nvaltryek-001/pollinex-ai/actions/workflows/ci.yml)
![Tests](https://img.shields.io/badge/automated%20tests-86%20passing-2e7d4f)
![Platforms](https://img.shields.io/badge/verified%20on-Ubuntu%20%7C%20Windows-1d3a2a)
![Python](https://img.shields.io/badge/python-3.11%2B-3776ab?logo=python&logoColor=white)
![React](https://img.shields.io/badge/react-18-61dafb?logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Three.js](https://img.shields.io/badge/three.js-3D-black?logo=threedotjs)
![License](https://img.shields.io/badge/code-MIT-blue)
![Data](https://img.shields.io/badge/training%20data-CC%20BY%204.0-e8a33d)

**Point a phone at a flower. Pollinex detects it, recognises the species (or honestly says _unknown_), reads its visible<br>
stage and health, explains whether it looks ready for pollination — and lets you simulate pollen transfer in 3-D.**

[Quick start](#-quick-start) ·
[Screenshots](#-screenshots) ·
[Features](#-features) ·
[How it works](#-how-it-works) ·
[Results](#-measured-results) ·
[Testing](#-testing--verification) ·
[Docs](#-documentation)

</div>

---

## 🌼 Why Pollinex?

Pollination decides yield, but the right method differs by crop: tomato needs **vibration**, apple and pear need **compatible
cross-pollen**, strawberry needs **every pistil covered**. Research systems that address this usually need robots, drones or
3-D rigs. Pollinex is the software-only counterpart: it runs on a **laptop and a phone browser**, uses public datasets and real
trained models, and **labels where every answer comes from** — so nothing looks more certain than it is.

<table>
<tr>
<td width="33%" valign="top">

### 📷 See
Upload or scan live with a laptop / phone camera. Flowers are detected with boxes and confidence; low-confidence results are
flagged, never hidden.

</td>
<td width="33%" valign="top">

### 🧠 Understand
Open-set species recognition, visible stage, flower centre, health cues and species-specific readiness — each tagged
**trained model**, **heuristic** or **rule engine**.

</td>
<td width="33%" valign="top">

### 🌀 Simulate
A seeded 3-D particle simulation of pollen release, drift and capture per crop — clearly a **computation**, never a claim of
fertilisation.

</td>
</tr>
</table>

---

## 📸 Screenshots

<sub>Captured automatically by Playwright from the running application in CI — real output, not mock-ups.</sub>

<table>
<tr>
<td width="62%" valign="top"><img src="docs/screenshots/desktop-02-scanner-results.png" alt="Scanner results with real detections"></td>
<td width="38%" valign="top"><img src="docs/screenshots/mobile-02-scanner-results.png" alt="Scanner on a phone"></td>
</tr>
<tr>
<td align="center"><b>Scanner</b> — 86 flowers detected, per-flower species, stage, readiness and provenance badges</td>
<td align="center"><b>Mobile</b> — same scanner on a Pixel 7 profile</td>
</tr>
</table>

<table>
<tr>
<td width="50%" valign="top"><img src="docs/screenshots/desktop-03-simulator.png" alt="3-D virtual pollination simulator"></td>
<td width="50%" valign="top"><img src="docs/screenshots/desktop-05-model-evaluation.png" alt="Model evaluation page"></td>
</tr>
<tr>
<td align="center"><b>Virtual simulator</b> — strawberry receptacle with many pistil targets</td>
<td align="center"><b>Model evaluation</b> — saved held-out test metrics, baseline &amp; ablation</td>
</tr>
<tr>
<td width="50%" valign="top"><img src="docs/screenshots/desktop-06-species.png" alt="Species knowledge base"></td>
<td width="50%" valign="top"><img src="docs/screenshots/desktop-04-dashboard.png" alt="Dashboard"></td>
</tr>
<tr>
<td align="center"><b>Species recognition</b> — 9-crop knowledge base with evidence</td>
<td align="center"><b>Dashboard</b> — metrics from real database records only</td>
</tr>
</table>

<details>
<summary><b>More screenshots</b> (landing, readiness, analytics, datasets, research — desktop &amp; mobile)</summary>
<br>

| | |
|---|---|
| ![Landing](docs/screenshots/desktop-01-landing.png) | ![Readiness](docs/screenshots/desktop-07-readiness.png) |
| ![Analytics](docs/screenshots/desktop-08-analytics.png) | ![Datasets](docs/screenshots/desktop-09-datasets.png) |
| ![Research](docs/screenshots/desktop-10-research.png) | <img src="docs/screenshots/mobile-03-simulator.png" width="300" alt="Mobile simulator"> |

All 20 captures live in [`docs/screenshots/`](docs/screenshots/).
</details>

---

## ✨ Features

| | Module | What it does | Evidence |
|:-:|---|---|:-:|
| 🔍 | **Flower detection** | Boxes, confidence, counts and low-confidence warnings from a detector trained in this repo (CPU). YOLO11 ONNX models plug in automatically. | `trained model` |
| 🌸 | **Species recognition** | Open-set reference gallery: says **unknown** below a calibrated threshold. One-click **manual correction** (original prediction kept, readiness re-estimated). Researchers add references for new species without retraining. | `reference gallery` |
| ⏳ | **Maturity stage** | Bud · early bloom · partially open · fully open · senescent, with score distribution and an *uncertain* flag. | `heuristic` |
| 🔬 | **Flower structures** | Petal and centre regions, pollen-like cluster. Anther, stigma, stamen and pistil shown as **not AI-validated** (no labelled data exists yet). | `heuristic` |
| 🩺 | **Visual health** | Browning, spots, discolouration, irregular outline — measurements only, **never a disease name**. | `heuristic` |
| 🎯 | **Pollination readiness** | Species-specific rules: strategy, supporting observations, confidence, uncertainty, biological limits and sources. | `rule engine` |
| 🧭 | **Pose & approach** | Image-space centre, facing estimate and alignment vector (explicitly *not* real-world distance). | `heuristic` |
| 🌀 | **3-D simulator** | Six species modes, particles with trails, play / pause / replay / speed, alignment & wind sweeps, 2-D fallback. | `simulation` |
| ⛅ | **Environment** | Manual records or Open-Meteo (conditions, source, timestamp); missing/stale-data warnings lower confidence. | — |
| 📱 | **Live scanner** | Laptop & phone cameras, permission handling, camera switching, sampled live inference with back-pressure, capture & save. | — |
| 📊 | **Analytics & reports** | Dashboard, trends, simulation history, model performance; PDF, CSV and JSON downloads. | — |
| 🔐 | **Platform** | JWT auth, **admin / researcher / user** roles, rate limiting, audit log, secure uploads (EXIF/GPS stripped), dark & light themes. | — |

<details>
<summary><b>All 20 pages</b></summary>
<br>

Landing · Sign in / Register · Dashboard · Flower scanner · Species recognition · Flower structure · Maturity stages ·
Pollination readiness · Plant health · Virtual simulator · Environment · Field management · Flower inventory · Pollination history ·
Model evaluation · Analytics · Research centre · Datasets · Reports · Admin settings
</details>

### 🌱 Supported crops

| Crop | Pollination strategy in the knowledge base | Simulator mode | Dataset images in repo | Detector | Species gallery |
|---|---|---|--:|:-:|:-:|
| 🍅 Tomato | vibration of poricidal anthers (buzz-like) | `vibration` | 0 | — | — |
| 🍆 Brinjal | vibration; long/medium-styled flowers set best | `vibration` | 0 | — | — |
| 🌶️ Chilli | brushing / gentle shaking | `brush` | 0 | — | — |
| 🍎 Apple | compatible cross-cultivar pollen | `cross_transfer` | 48 | ✅ | ✅ |
| 🍐 Pear | compatible cross-cultivar pollen | `cross_transfer` | 18 | ✅ | ✅ |
| 🍑 Peach | mostly self-fertile; brush supplement | `brush` | 24 | ✅ | ✅ |
| 🍓 Strawberry | even coverage of all pistils | `air_assisted` | 0 | — | — |
| 🌻 Sunflower | ring-by-ring floret progression | `ring_progression` | 628 | ❌ not trained | ✅ |
| 🌺 Hibiscus | pollen onto five stigma pads | `column_transfer` | 0 | — | — |

> **Verified 2026-11-03** ([full audit](docs/FINAL_PROJECT_AND_DATASET_AUDIT.md)): 718 real dataset images, all annotated with boxes;
> **no images exist for tomato, brinjal, chilli, strawberry or hibiscus**, and no anther/stigma annotations exist for any crop.
> Crops without references return **unknown** until reference images are added — or the user selects the species.
> New crops are added with one JSON entry + reference photos; no code changes.

---

## 🚀 Quick start

### Windows (recommended)

> Needs **Python 3.12** ([python.org](https://www.python.org/downloads/), tick *Add python.exe to PATH*), **Node.js 20+**, **Git**.
> No GPU, no paid API, no hardware.

```powershell
git clone https://github.com/nvaltryek-001/pollinex-ai.git
cd pollinex-ai
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1    # venv, pinned packages, npm, .env, dependency check
powershell -ExecutionPolicy Bypass -File scripts\run_windows.ps1      # API :8000 + app :5173, opens your browser
```

Open **http://localhost:5173**, register (the **first account becomes admin**) and go to **Flower scanner**.
Try `tests/fixtures/sample_orchard.jpg`. API docs: **http://localhost:8000/docs**.

<details>
<summary><b>Linux / macOS</b></summary>

```bash
git clone https://github.com/nvaltryek-001/pollinex-ai.git && cd pollinex-ai
scripts/setup_dev.sh        # venv + pip + npm + .env
scripts/run_dev.sh          # API :8000, app :5173
```
</details>

<details>
<summary><b>Docker Compose (PostgreSQL)</b></summary>

```bash
cp .env.example .env        # set POSTGRES_PASSWORD and JWT_SECRET
docker compose up --build   # app http://localhost:8080 · API http://localhost:8000/docs
```
</details>

<details>
<summary><b>PostgreSQL on Windows</b></summary>

```powershell
# local PostgreSQL (or: docker run -p 5432:5432 -e POSTGRES_USER=pollinex -e POSTGRES_PASSWORD=... -e POSTGRES_DB=pollinex postgres:16)
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1 -Postgres -PgPassword "your-password"
```
Writes `DATABASE_URL` to `.env` and applies the Alembic migrations. Without it, SQLite (`backend\pollinex.db`) is used.
</details>

<details>
<summary><b>📱 Using your phone's camera</b></summary>

Browsers only allow the camera on **HTTPS** (or `localhost`). Start the app, then expose it with a tunnel:

```powershell
cloudflared tunnel --url http://localhost:5173
```
Open the `https://…trycloudflare.com` address on your phone. Image upload works everywhere, and on phones the upload button
can open the camera directly.
</details>

<details>
<summary><b>Manual commands (no scripts)</b></summary>

```powershell
python -m venv .venv; .venv\Scripts\activate
pip install -r backend\requirements.txt -c backend\requirements.lock.txt
cd backend; uvicorn app.main:app --reload            # terminal 1
cd frontend; npm ci; npm run dev                     # terminal 2
python scripts\check_dependencies.py                 # verify everything
```
</details>

---

## 🧩 How it works

```mermaid
flowchart LR
  A["📷 Photo or<br/>camera frame"] --> B{"Mode"}
  B -- "scene / auto" --> C["🔍 Detector<br/>boxes + confidence"]
  B -- "close-up" --> C2["Close-up fallback<br/>(labelled)"]
  C --> D["🌸 Species gallery<br/>open-set → unknown"]
  C2 --> D
  D --> E["⏳ Stage · 🔬 structures<br/>🩺 health · 🧭 pose"]
  E --> F["🎯 Readiness rules<br/>species KB + ⛅ environment"]
  D -. "user corrects species" .-> F
  F --> G[("💾 Scans · history<br/>analytics · reports")]
  F --> H["🌀 3-D simulator"]
  H --> I["Simulated transfer<br/>≠ fertilisation"]
```

<details>
<summary><b>System architecture</b></summary>

```mermaid
flowchart LR
  subgraph Browser["React + Vite (phone / laptop)"]
    UI[20 pages · Tailwind · Recharts]
    CAM[Camera API · frame sampler]
    SIM3D[Three.js replay · 2-D fallback]
  end
  subgraph API["FastAPI"]
    AUTH[JWT · roles · rate limits]
    SCAN[scans · live WebSocket]
    AI[AI module endpoints]
    SIMR[simulations]
    REC[fields · plants · environment · logs]
    AN[analytics · reports · admin]
  end
  subgraph Engine["ai-engine (pure Python, CPU)"]
    DET[detector: pixel-HGB or YOLO11-ONNX]
    GAL[open-set species gallery]
    HEU[stage · structure · health · pose]
    KB[(species knowledge base)]
    RUL[readiness rule engine]
  end
  SIMP[simulation: seeded particle model]
  DB[(PostgreSQL / SQLite)]
  FS[(image storage · EXIF stripped)]
  OM[(Open-Meteo, optional)]
  UI --> API
  CAM --> SCAN
  SIM3D --> SIMR
  SCAN --> DET --> GAL --> HEU --> RUL --> KB
  SIMR --> SIMP
  API --> DB
  SCAN --> FS
  REC --> OM
```
More: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md)
</details>

---

## 📈 Measured results

<sub>From `ai-engine/reports/*.json` — held-out test split used once, parameters chosen on validation, 2-vCPU CPU machine.
Data: USDA Multi-species Fruit Flower (apple, peach, pear) — 90 images, 4,651 instances, group-aware splits 54 / 14 / 22.</sub>

<table>
<tr>
<td align="center" width="25%"><h2>0.410</h2>detector mAP@0.5<br><sub>test split</sub></td>
<td align="center" width="25%"><h2>0.191</h2>detector mAP@0.5:0.95<br><sub>test split</sub></td>
<td align="center" width="25%"><h2>3.2×</h2>better than baseline<br><sub>vs. Otsu threshold (0.127)</sub></td>
<td align="center" width="25%"><h2>0.819</h2>open-set species accuracy<br><sub>apple · peach · pear · unknown</sub></td>
</tr>
</table>

<details>
<summary><b>Detector baseline &amp; ablation (same protocol)</b></summary>

| Variant | val mAP50 | **test mAP50** | test mAP50-95 | Precision | Recall | ms / image |
|---|---|---|---|---|---|---|
| A · Otsu "whiteness" threshold (no learning) | 0.110 | 0.127 | 0.062 | 0.046 | 0.451 | 11 |
| B · boosted trees, 12 colour features | 0.276 | 0.240 | 0.109 | 0.059 | 0.593 | 4,664 |
| C · boosted trees, 36 colour/texture features | 0.491 | 0.405 | 0.186 | 0.167 | 0.626 | 9,569 |
| **C · deployed (1280 px, stride 2)** | **0.506** | **0.410** | **0.191** | 0.169 | 0.610 | **1,990** |
| C · live scan (800 px, stride 2) | 0.384 | 0.305 | 0.129 | 0.215 | 0.439 | 676 |

Per-species test mAP50: apple 0.395 · peach 0.491 · pear 0.420. Recall by size: small 0.47 · medium 0.64 · large 0.75.
Precision is low because pale bark and unlabelled background blossoms count as false positives. This is a modest CPU baseline;
no comparison with published deep detectors is claimed.
</details>

<details>
<summary><b>Species gallery (open-set)</b></summary>

| Metric | Value |
|---|---|
| Open-set accuracy / macro-F1 | 0.819 / 0.799 |
| Accuracy on flower crops only | 0.931 |
| Background crops rejected as `unknown` | 0.468 |
| Leave-one-species-out → `unknown` | apple 0.435 · peach 0.919 · pear 0.219 |

Each species in this dataset was photographed with a different camera, so species and capture conditions are confounded —
these numbers validate the open-set *mechanism*, not field-general recognition.
</details>

**Sunflower extension** (`species_extension_evaluation.json`, `detector_on_tf_flower_detection_sunflower.json`): gallery recall 0.937 on 95
held-out close-up crops; apple/peach/pear accuracy after extension 0.934; deployed detector on sunflower test mAP@0.5 0.001 (not trained on it).

**Not measured** (and never presented as measured): stage, structure, health and pose heuristics (no labels exist), readiness
rules (no biological ground truth), simulation outcomes (no field trial), YOLO11 (not trained yet).

---

## 🌀 Virtual pollination simulator

A seeded particle model (release → drift, wind, turbulence → capture) computed by the backend and replayed in Three.js.

| Mode | Crops | What is modelled |
|---|---|---|
| `vibration` | tomato, brinjal | anther cone releases pollen when vibrated (peak near 150–200 Hz) onto the stigma below |
| `cross_transfer` | apple, pear | pollen carried from a **separate compatible donor flower** |
| `brush` | chilli, peach | anther ring → central stigma |
| `air_assisted` | strawberry | coverage of ~60 pistils on the receptacle |
| `ring_progression` | sunflower | pollen-presenting ring → inner receptive floret ring |
| `column_transfer` | hibiscus | staminal column → five stigma pads |

Results always show four separate things: **detection accuracy** · **simulation completion** · **simulated transfer efficiency** ·
**biological outcome = not measured**. Assumptions and limits: [`docs/SIMULATOR_DOCUMENTATION.md`](docs/SIMULATOR_DOCUMENTATION.md).

---

## ✅ Testing & verification

Every push to `main` runs the full stack on clean **Ubuntu and Windows** machines in GitHub Actions — all green.

| Check | Result |
|---|:-:|
| AI engine + simulator tests | ✅ 37 |
| Backend API, auth, roles, DB, uploads, inference | ✅ 24 |
| Frontend unit & component tests (Vitest) | ✅ 11 |
| Playwright end-to-end — desktop + Pixel 7, **simulated camera**, live scan, species correction, every page | ✅ 14 |
| TypeScript strict type-check · production build | ✅ |
| Migrations on **PostgreSQL 16** and SQLite · backend startup | ✅ |
| Docker images + Docker Compose smoke test | ✅ |
| **Windows**: `setup_windows.ps1` → `test_windows.ps1 -E2E` → backend health | ✅ |

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_windows.ps1 -E2E   # everything, locally
python scripts\check_dependencies.py                                     # environment check
```
`backend/requirements.lock.txt` and `frontend/package-lock.json` pin the exact versions tested in CI.
Full results and fixes: [`docs/TESTING_REPORT.md`](docs/TESTING_REPORT.md).

---

## 🛠 Tech stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18 · Vite 5 · TypeScript · Tailwind CSS · Recharts · Three.js · lucide-react |
| **Backend** | FastAPI · Pydantic 2 · SQLAlchemy 2 · Alembic · PyJWT · WebSocket · ReportLab |
| **AI (runtime)** | NumPy · SciPy · OpenCV · scikit-learn · scikit-image · onnxruntime — **no PyTorch needed to run** |
| **AI (optional training)** | Ultralytics YOLO11 + PyTorch → ONNX (Google Colab guide included) |
| **Database** | PostgreSQL 16 (Docker / production) · SQLite (local, zero setup) |
| **Testing** | Pytest · Vitest + Testing Library · Playwright · Ruff |
| **Ops** | Docker · Docker Compose · GitHub Actions (Ubuntu + Windows) · Render &amp; Vercel configs |

---

## 🗂 Project structure

```
pollinex-ai/
├── frontend/          React app — pages/, components/, lib/, e2e/ (Playwright)
├── backend/           FastAPI — routers/, services/, models.py, alembic/ migrations, tests/
├── ai-engine/         pollinex_ai (detector, species, stage, structure, health, pose, readiness, knowledge base)
│   ├── training/      reproducible training & evaluation scripts (incl. YOLO11)
│   ├── models/        small shipped models
│   └── reports/       evaluation JSON + figures
├── simulation/        pollinex_sim particle engine + tests
├── datasets/          manifest, sources, licences, prep scripts, CVAT workflow, splits, audit reports
├── research/          literature review, gaps, comparison, methodology, references (.bib)
├── docs/              architecture, API, models, datasets, simulator, testing, reports, screenshots
├── scripts/           Windows (.ps1) + bash setup / run / test, dependency checker
└── deployment/        Render blueprint (Vercel config in frontend/)
```

---

## 📚 Datasets & research

| Dataset | Licence | Status |
|---|---|---|
| **Multi-species Fruit Flower** — Dias, Tabb & Medeiros (2018), USDA Ag Data Commons, [doi:10.15482/USDA.ADC/1423466](https://doi.org/10.15482/USDA.ADC/1423466) | CC BY 4.0 | ✅ integrated (train / eval / gallery) |
| TensorFlow Flower Detection (INESC TEC, [Zenodo 7768292](https://zenodo.org/records/7768292)) + species from TF `flower_photos` (CC-BY Flickr) | CC BY 4.0 | ✅ sunflower subset: 628 images, 2,432 boxes (gallery + detection data) |
| INESC Flower Detection ([Zenodo 7708815](https://zenodo.org/records/7708815)) | CC BY 4.0 | audited, not used (species unknown, split leakage) |
| Oxford 102 Flowers (Nilsback & Zisserman, 2008) | research use (unverified) | script ready; host unreachable from build env and CI |
| FlowerNet ([Mendeley](https://data.mendeley.com/datasets/26nvt3t27m)) | MIT | ingest script (originals only) |
| EWD wildflowers · DoPI · FloPE · PlantCLEF | various | documented, not ingested — reasons in the manifest |

> **Data audit:** the upstream per-image boxes are often vertically flipped relative to the images, so Pollinex derives its
> ground truth from the masks instead. See [`datasets/reports/`](datasets/reports/).

**Key references** — FloPE (Shrestha et al., IROS 2025) · Artificial Pollination Technologies (Broussard et al., *Agronomy* 2023) ·
Autonomous Flower Pollination review (Zhang et al., *Comput. Electron. Agric.* 2025) · Robot-based Pollinators (Singh et al.,
*AI Review* 2025) · Data-centric wildflower monitoring (Schouten et al., *PLOS ONE* 2024) · DoPI (Balfour et al., *Ecology* 2022).
Full review, gaps and BibTeX: [`research/`](research/).

---

## ⚠️ Limitations

- The detector is trained on **apple, peach and pear** orchard photos only; precision is low on cluttered scenes.
- Five crops (tomato, brinjal, chilli, strawberry, hibiscus) have **no images at all** — they return *unknown* unless declared or references are added.
- Sunflower is recognised by the species gallery (93.7 % recall on held-out close-ups) but the **detector does not find sunflowers** (mAP@0.5 0.001).
- **No anther / stigma detector**: structures, stage, health and pose are labelled heuristics until annotated data exists.
- Readiness is a **visual estimate**; simulation is **computation** — neither proves pollen viability or fertilisation.
- Camera is verified with a simulated camera and phone emulation; test on your own phone over HTTPS.
- **No public deployment yet** (Render + Vercel configs are ready).

## 🔭 Roadmap

- [ ] Train YOLO11 on GPU ([Colab guide](docs/AI_MODEL_DOCUMENTATION.md)) and compare on the same test split
- [x] Sunflower references + held-out evaluation (TF Flower Detection subset)
- [ ] Train a detector on the committed sunflower YOLO data
- [ ] Collect and annotate images (CVAT workflow included) for hibiscus, tomato, strawberry, brinjal and chilli
- [ ] Trained stage and reproductive-structure models
- [ ] Field trial: natural vs manual vs app-assisted pollination ([design](research/methodology.md))
- [ ] Public deployment and offline-capable PWA

---

## 📖 Documentation

| | |
|---|---|
| [Project completion report](docs/PROJECT_COMPLETION_REPORT.md) | [Testing report](docs/TESTING_REPORT.md) |
| [Architecture](docs/ARCHITECTURE.md) · [Database schema](docs/DATABASE_SCHEMA.md) | [API documentation](docs/API_DOCUMENTATION.md) (live at `/docs`) |
| [AI models](docs/AI_MODEL_DOCUMENTATION.md) | [Datasets](docs/DATASET_DOCUMENTATION.md) |
| [Simulator](docs/SIMULATOR_DOCUMENTATION.md) | [Research methodology](docs/RESEARCH_METHODOLOGY.md) |
| [Installation](docs/INSTALLATION_GUIDE.md) · [Deployment](docs/DEPLOYMENT_GUIDE.md) | [User manual](docs/USER_MANUAL.md) |
| [**Final project & dataset audit**](docs/FINAL_PROJECT_AND_DATASET_AUDIT.md) | [Completion audit](docs/PROJECT_COMPLETION_AUDIT.md) · [Next steps](docs/NEXT_SESSION_TASKS.md) |

---

## 📄 Licence & citation

Code: **MIT** ([LICENSE](LICENSE)). Trained models and test images derive from the USDA Multi-species Fruit Flower dataset
(**CC BY 4.0**) — please cite Dias, Tabb & Medeiros (2018), [doi:10.1109/LRA.2018.2849498](https://doi.org/10.1109/LRA.2018.2849498)
and [doi:10.15482/USDA.ADC/1423466](https://doi.org/10.15482/USDA.ADC/1423466).
Contributing: [CONTRIBUTING.md](CONTRIBUTING.md) · Security: [SECURITY.md](SECURITY.md) · Changes: [CHANGELOG.md](CHANGELOG.md)

<div align="center">
<sub>🌼 Built to be honest about what a photo can and cannot tell you about pollination.</sub>
</div>
