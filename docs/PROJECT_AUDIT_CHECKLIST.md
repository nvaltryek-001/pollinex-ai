# Master requirements checklist (2026-11-04)

Each requirement was checked against the code, data, models and tests, not against the docs. A page existing does not
count as done.

**Status codes:**
* **T**: implemented and tested; an automated test ran in CI.
* **V**: implemented, but not fully validated; works, with no or partial automated coverage or evidence.
* **P**: partially implemented.
* **M**: missing.
* **B**: blocked by unavailable data or external access.

## Application modules (Part 7)
| # | Requirement | Status | Evidence / gap |
|--:|---|:-:|---|
| 1 | Landing page | T | Screenshot E2E test; links into register and login |
| 2 | Registration and login | T | Backend auth tests; E2E register and login flows; password policy (Vitest) |
| 3 | Dashboard | T | DB-backed totals (`test_dashboard_reflects_database`); E2E page sweep; no sideways scroll on a phone |
| 4 | Image upload | T | Validation, EXIF strip and real inference (backend); E2E upload |
| 5 | Live camera scanning | T* | E2E with a fake camera, live frames and permission denied. *Not tested on a real phone over HTTPS* |
| 6 | Flower detection | T | YOLO11n ONNX, engine ONNX tests, reproducible test metrics. One `flower` class; no boxes for 5 species |
| 7 | Species recognition | T | Gallery and crop/scene blend, both selected on validation; strawberry rejected as unknown; correction flow (E2E) |
| 8 | Species information | T | `species_botany.json` for 9 species; loader validation test; E2E panel for all 9 species |
| 9 | Botanical analysis (visible) | V | Centre-region / petal heuristics, labelled `heuristic` |
| 10 | Reproductive-structure analysis | P | Heuristic plus a hook for a trained model. **0 structure annotations, so no model.** Schema now includes sepal |
| 11 | Flower maturity analysis | P | Stage heuristic with distribution and uncertainty. No stage labels, so no ML claim |
| 12 | Pollination readiness | T | Rule engine; inputs, uncertainty and limitations shown; engine tests |
| 13 | Virtual simulator | T | Simulator tests; E2E run, replay and disclaimer |
| 14 | Environmental information | T | Backend CRUD; Open-Meteo off in tests; E2E sweep |
| 15 | Scan history | T | E2E opens a saved scan; pagination; isolation between users |
| 16 | Scan details | T | Provenance and limitations card, species panel, blend explanation; E2E |
| 17 | Analytics | T | Computed from records; E2E sweep |
| 18 | PDF reports | T | Summary PDF and per-scan PDF (backend tests; E2E download) |
| 19 | CSV reports | T | Backend test, formula-injection guard, E2E download |
| 20 | User settings | T | Display name, password change (revokes sessions), theme; backend and E2E tests |
| 21 | Help and documentation | T | `/app/help`; E2E sweep |
| — | Admin settings | T (API) | Role change, last-admin guard, detector switch (backend). The UI page is not in the E2E sweep |
| — | Logout and route protection | T | E2E logout, then `/app/history` redirects to `/login` |

## Data (Part 2)
| Requirement | Status | Evidence / gap |
|---|:-:|---|
| 9-species image inventory from disk | T | `species_inventory.json`; integrity test (decode, labels, cross-split duplicates) |
| USDA, TF Flower Detection, iNaturalist, Commons | T | Downloaded, licensed per file, attribution kept |
| More strawberry, brinjal and chilli photos | B | iNaturalist (open licence + flowering annotation) and the Commons flower categories are exhausted (15 and 29 strawberry). Own photos are needed |
| Oxford 102 | B | Hosts unreachable from the workspace and from GitHub runners; script only |
| FlowerNet | B | Manual download required; ingest script only |
| PlantCLEF | B | Terms not verified; very large; not downloaded |
| Eindhoven Wildflower, DoPI, FloPE | B | Licence or scope mismatch, or no download; documented only |

## Models and research (Parts 3–6, 8)
| Requirement | Status | Evidence / gap |
|---|:-:|---|
| Nine-species detection | P / B | Proposals for 1,267 photos, a verified-only importer and a gated trainer exist. **Status `pending_verified_annotations`**: human review in CVAT is needed |
| Per-species detection metrics | T (4 species) | apple, peach, pear, sunflower. None claimed for the other 5 |
| Structure detector (anther, stigma, stamen, pistil, petal, sepal) | B | Schema, guidelines, batch builder and model hook exist; 0 annotations |
| ML maturity classifier | B | Needs the `stage` attribute on reviewed boxes |
| Auto-mode species weakness | T | Fixed by a crop/scene blend chosen on validation; test auto accuracy 0.704 → 0.806 (and 0.832 with rejection references) |
| Strawberry / unsupported species | T | Rejection-only references; strawberry → unknown on 4 of 6 test photos (was 0); never returned as strawberry |
| Confidence calibration | P | Abstention thresholds were tested on validation and **not adopted** (they lowered macro-F1). The `uncertain` flag below a 0.60 vote share remains |
| Model cards, data-flow diagrams, ethics and licensing | T | `MODEL_CARDS.md`, `ARCHITECTURE.md` (diagrams checked with mmdc), `ETHICS_AND_LICENSING.md` |
| Reproducibility | T | `evaluate_deployed_models.py` (`[evaluate]` workflow), `*_rule.py` decision scripts with saved reports |
| Fruit recognition | B | No dataset; stated in the UI, the PDF and the docs |

## Platform (Parts 9–11)
| Requirement | Status | Evidence / gap |
|---|:-:|---|
| SQLite local, PostgreSQL production, migrations | T | CI: Alembic up/down/up on SQLite and PostgreSQL 16; `postgres://` URL mapping test |
| Persistent data on Render | **B** | The `pollinex-db` URL must be pasted into `DATABASE_URL` by the owner. Health currently reports `database_backend: sqlite` |
| Render deployment, health, API docs | T | Live smoke workflow; `/docs` |
| Automatic GitHub → Render deploy | **B** | Render's GitHub app needs access to the repository (owner action). Deploys are started manually |
| Vercel | B | HTTP 403 for the connected account; optional |
| Docker | T | CI builds the image (frontend stage included) |
| Security controls | T | `SECURITY_AUDIT.md`; pip-audit clean |
| npm advisories | P | Shipped bundle: 2 moderate (react-router 6). Dev tooling: high and critical in vitest/tinypool. All are major upgrades, planned separately |
| Windows fresh clone | T | CI `windows-latest`: setup, tests and E2E; `LOCAL_SETUP.md` covers N:\ |
