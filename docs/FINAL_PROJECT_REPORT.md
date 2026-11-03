# POLLINEX AI — Final Project Report & Audit

_Date: 2026-11-02 · Build environment: 2 vCPU Linux VM, no GPU; outbound access limited to GitHub (PyPI, npm, Docker Hub,
Hugging Face, Zenodo, arXiv blocked)._

## 1. Summary
POLLINEX AI is a software-only, research-oriented platform for flower detection, open-set species recognition, heuristic
stage/structure/health analysis, species-specific pollination-readiness decision support, environmental context and virtual
pollination simulation, delivered as a FastAPI backend, pure-Python AI and simulation packages, and a React web app with a
phone camera scanner.

## 2. Implemented features
* Literature review (6 required sources + 7 supporting), comparison matrix, 5 research gaps, methodology, BibTeX/JSON references.
* Dataset engineering: verified manifest of 10 sources; full preparation of the USDA fruit-flower set with leakage-safe splits,
  duplicate/quality audit, and discovery of an upstream box-orientation defect; scripts for 3 more datasets; CVAT workflow.
* Trained CPU flower detector with baseline + ablation + speed/accuracy study; real test metrics.
* Open-set species gallery with calibrated threshold, leave-one-species-out evaluation, runtime extension by researchers.
* Heuristic modules: stage (5 classes), centre region, visible health, image-space pose & approach guidance — all labelled.
* 9-species knowledge base with mechanisms, compatibility, stages, strategies, environment ranges, evidence and limitations;
  explainable readiness engine.
* Seeded particle simulator with 6 species-specific modes, sweeps, persistence and replay; Three.js + 2-D UI.
* Backend: 50+ endpoints, JWT roles, uploads, live WebSocket, environment (manual + Open-Meteo), records, analytics from DB,
  CSV/PDF/JSON reports, admin, audit log, Alembic migration, Docker/Compose/Render/Vercel/CI configs.
* Frontend: all 20 required pages, dark/light theme, responsive layout, provenance badges everywhere.

## 3. Partially implemented
* **YOLO11 detector** — training/export script and ONNX inference backend written; not trained (no PyTorch).
* **Web stack verification** — backend test suite (20 tests), Vitest and Playwright suites written; not executed (no FastAPI,
  SQLAlchemy or npm packages available). The AI and simulation code they call is executed and tested.
* **Species coverage** — 3 of 9 crops have evaluated references; others rely on user declaration or future references.
* **Screenshots** — not produced (frontend could not be built in the environment).

## 4. Not implemented
* Reproductive-structure (anther/stigma) **detection model** — no licensed annotations; heuristic + annotation pipeline instead.
* Trained stage classifier — no stage labels; heuristic instead.
* Public deployment — no hosting credentials/Docker daemon.
* Biological validation of readiness or simulation — requires physical trials (design provided).

## 5. Dataset sources & licence status
| Dataset | Licence | Status |
|---|---|---|
| USDA Multi-species Fruit Flower | CC BY 4.0 | integrated |
| TF Flower Detection (Zenodo 7768292) | CC BY 4.0 | script only |
| Oxford 102 | unverified (research use) | script only |
| FlowerNet | MIT | script only |
| EWD | CC BY-NC 4.0 | documented only |
| DoPI | no formal licence; citation requested | documented only |
| FloPE data | not stated | documented only |
| PlantCLEF | unverified | unverified |

## 6. Actual model evaluation metrics (test split, used once)
| Model | Metric | Value |
|---|---|---|
| Detector (deployed: 1280 px, stride 2) | mAP@0.50 / mAP@0.50:0.95 | **0.410 / 0.191** |
| | precision / recall @0.5 (all predictions) | 0.169 / 0.610 |
| | latency (2 vCPU) | ~2.0 s full, ~0.7 s live (800 px) |
| Baseline: Otsu whiteness | mAP@0.50 | 0.127 |
| Ablation: colour-only features | mAP@0.50 | 0.240 |
| Species gallery | open-set accuracy / macro-F1 | 0.819 / 0.799 |
| | background rejection | 0.468 |
| | leave-one-species-out → unknown | apple 0.435, peach 0.919, pear 0.219 |

## 7. Test results
35/35 executed tests pass (AI engine 19, simulation 16). Report generation and the end-to-end pipeline were exercised.
Backend (20), frontend unit (≈12) and E2E (3 × 2 devices) suites are written but unexecuted here. Details: `TESTING_REPORT.md`.

## 8. Deployment URLs
None — not deployed from the build environment. Configurations: `docker-compose.yml`, `deployment/render.yaml`, `frontend/vercel.json`.

## 9. GitHub repository
See the README header / the push log in the session summary. Pushed only after remote confirmation.

## 10. Installation
`docs/INSTALLATION_GUIDE.md` (local, Windows notes, Docker).

## 11. Remaining risks
1. **First full build**: frontend and API code have not been compiled/run against their dependencies; expect small fixes
   (TypeScript types, library API drift). Mitigation: CI + `scripts/run_tests.sh`.
2. **scikit-learn pin** (1.9.1) for the pickled detector; retraining script provided.
3. **Detector precision** is low on cluttered orchard scenes; close-ups of non-orchard crops rely on the fallback.
4. **Species confound** may overstate species accuracy.
5. **Knowledge-base rules** are general; local agronomic validation needed before field use.
6. **AGPL-3.0** obligations if the optional YOLO11 path is deployed.

## 12. Honest completion
**≈ 70 %.** Research, data engineering, AI training/evaluation, simulation and documentation are complete and evidenced. The
full-stack application is implemented but awaits its first build and test run on a machine with package-registry access; deep
detection, structure detection and deployment remain open.
