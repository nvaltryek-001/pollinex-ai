# Project audit checklist (2026-11-04)

Status key:
* **Implemented + tested**: covered by an automated test that ran in CI.
* **Implemented, manual check**: works when tried by hand, but no automated test covers it.
* **Incomplete**: a part of the feature is missing.
* **Not available**: no model or data exists, and the app says so.

A page existing was never counted as "working".

## Application modules (21)

| Module | Status | Evidence / notes |
|---|---|---|
| Dashboard | Implemented + tested | E2E page sweep and small-screen test. Totals come from the database (backend `test_dashboard_reflects_database`). |
| Scanner (upload) | Implemented + tested | E2E: register → upload → real detections → species correction → history. Backend: upload validation and real inference. |
| Scanner (camera / live) | Implemented + tested | E2E with a fake camera device; a permission-denied error test. |
| Species identification | Implemented + tested | Gallery classification (engine tests); E2E info panel for all 9 species. Strawberry is shown as *not AI-supported*. |
| Flower detection | Implemented + tested | YOLO11n ONNX; engine ONNX tests; test-set metrics reproduced by `scripts/evaluate_deployed_models.py`. Detection is evaluated for apple, peach, pear and sunflower only. |
| Flower structures | Implemented (heuristic) | Centre-region colour heuristic, labelled as such. **Incomplete:** there are 0 structure annotations, so no trained structure model exists. |
| Maturity analysis | Implemented (heuristic) | Stage heuristic with distribution and uncertainty; no trained stage model. |
| Pollination readiness | Implemented + tested | Rule-based. Inputs, uncertainty and limitations are shown; engine tests cover it. |
| Virtual simulator | Implemented + tested | E2E run/replay/disclaimer; simulator unit tests. |
| Environment information | Implemented + tested | Backend CRUD tests; E2E page sweep. |
| Plant health | Implemented (heuristic) | Visible colour anomalies only, with no disease claims. |
| Field management | Implemented + tested | Backend CRUD and ownership tests; E2E page sweep. |
| Inventory | Implemented + tested | Backend CRUD tests; E2E page sweep. |
| Scan history | Implemented + tested | E2E opens a saved scan; backend checks pagination and isolation between users. |
| Scan results / detail | Implemented + tested | Provenance and limitations card, species panel, and PDF/CSV/JSON export (E2E downloads; backend `/reports/scans/{id}.pdf`). |
| Model evaluation | Implemented + tested | Page reads committed reports; E2E page sweep. |
| Dataset management | Implemented + tested | Page error boundary added after a crash was found; E2E page sweep. |
| Analytics | Implemented + tested | Computed from the user's records; E2E page sweep. |
| Research centre | Implemented + tested | 50 papers checked against OpenAlex; E2E page sweep. |
| Reports | Implemented + tested | Summary PDF, scans CSV, per-scan PDF (backend tests). |
| Admin settings | Implemented + tested (API) | Backend: role change, last-admin protection, activity log, detector switch. The UI page is not in the E2E sweep, because the E2E user is not always the first account and therefore not always admin. |
| Authentication and roles | Implemented + tested | Register/login/refresh/revoke tests; role guards (`scope=all` requires researcher/admin). |
| Help and documentation | Implemented + tested | New in this release; E2E page sweep. |

## AI, data and knowledge

| Item | Status | Notes |
|---|---|---|
| Datasets (1,985 images, 9 species) | Implemented + tested | `test_dataset_integrity_audit_passes`: every image decodes, labels are valid, no cross-split exact duplicates, leakage exclusion applied. |
| Detector metrics | Reproduced | USDA test mAP@0.5 0.593 / mAP@0.5:0.95 0.332; sunflower 0.871 / 0.694 (`docs/MODEL_EVALUATION_RESULTS.md`). |
| Species gallery metrics | Reproduced | Test accuracy 0.874, macro-F1 0.862, 1,182 items, confusion matrix in the results doc. |
| Species knowledge base (9 species) | Implemented + tested | `species_botany.json` plus validation in the loader (`docs/SPECIES_KNOWLEDGE_BASE.md`). |
| Fruit recognition | Not available | No dataset or model. Stated in the UI, the PDF and the docs; a future workflow is documented. |
| Reproductive-structure model | Not available | CVAT workflow and batch builder exist, but there are 0 annotations. |

## Deployment

| Item | Status | Notes |
|---|---|---|
| Render web service (UI + API, one origin) | Implemented, verified live | Read-only smoke workflow `[smoke]`. |
| ONNX model loads in production | Verified live | `/api/v1/health` reports `yolo11-onnx` and 8 gallery species. |
| Persistent PostgreSQL | **Incomplete (needs owner action)** | The `pollinex-db` instance exists. Its connection string is not readable through the tools available to the assistant, and secrets must not be committed. The owner must paste the Internal Database URL into `DATABASE_URL` (see `DEPLOYMENT_GUIDE.md`). Until then, data is lost on restart. |
| Migrations | Implemented + tested | Alembic upgrade at start (`AUTO_CREATE_TABLES=false`); CI runs migrations on PostgreSQL 16. |
| GitHub → Render auto-deploy | **Incomplete (needs owner action)** | The service has `autoDeploy: yes`, but pushes did not start deploys, which points to the Render GitHub app lacking access to the repo. Deploys were triggered manually. |
| Vercel | **Blocked (HTTP 403)** | The connected account refuses project creation. The app does not need Vercel, because Render serves the UI. |
| Secrets | OK | `JWT_SECRET` is set only on Render; nothing secret is in git. |
| CORS / security | OK | Same-origin UI; `CORS_ORIGINS` is limited to the Vercel origin; production refuses to start without `JWT_SECRET`; rate limits on auth and scans. |
