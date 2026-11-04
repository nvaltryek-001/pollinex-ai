# Final Project & Dataset Audit

> **Superseded on 2026-11-04 by [`FINAL_RELEASE_REPORT.md`](FINAL_RELEASE_REPORT.md).** The numbers below are the audit as of commit
> `d434111`: 718 images, no YOLO11, and a 4-species gallery. They are kept for history.

_Audit date: 2026-11-03. Every number below was produced by a script or a test run in this audit, not copied from earlier
documents. The image inventory is `datasets/reports/dataset_inventory.{json,md}`, re-created by
`python datasets/scripts/audit_datasets.py`._

Legend: ✅ implemented and executed/tested · 🟡 implemented and runs, but a heuristic or partially validated · ❌ missing

---

## 1. Summary

| Question | Verified answer |
|---|---|
| Is the source code complete? | Yes. There are 2,376 tracked files: backend, AI engine, simulator, frontend (19 page files, 23 routes), migrations, scripts, CI and documentation. |
| Are datasets downloaded? | **Partly.** 2 of 12 listed sources have images committed: USDA (apple/peach/pear) and the TF Flower Detection sunflower subset. 1 is used only as a label source, 1 was audited and rejected, and 1 cannot be reached. The rest are scripts or documentation only. |
| How many real dataset images are in the repo? | **718** unique images (90 USDA + 628 sunflower). There are also **628 derived sunflower crops**, which are counted separately and never added to the image total. |
| How many species have images? | **4 of 9**: apple 48, peach 24, pear 18, sunflower 628. **Hibiscus, tomato, strawberry, brinjal and chilli have 0.** |
| Detector supports | Apple, peach and pear only. On sunflower it scores test mAP@0.5 = 0.001, which in practice means it does not work. |
| Species gallery supports | Apple, peach, pear and sunflower. Sunflower recall is 93.7% on 95 held-out close-up crops. |
| Anther / stigma annotations | **None exist** for any species. Structure outputs are heuristics, labelled as such in the UI. |

## 2. Repository and source-code audit

| Area | Location | Files verified |
|---|---|---|
| Backend (FastAPI) | `backend/app/` | 7 routers, 7 services, `models.py` (19 ORM tables), `security.py`, `config.py`. Router decorators: 57 HTTP + 1 WebSocket. |
| Migrations | `backend/alembic/versions/` | `0001_initial_schema.py`, `0002_species_correction.py` |
| AI engine | `ai-engine/pollinex_ai/` | `detector`, `features`, `species`, `maturity`, `structure`, `regions`, `health`, `pose`, `readiness`, `pipeline`, `metrics`, plus `knowledge/species_kb.json` (9 species) |
| Training / evaluation | `ai-engine/training/` | detector, species gallery, inference trade-off, YOLO11 recipe, **`extend_gallery.py` (new)**, **`evaluate_detector_on.py` (new)** |
| Models | `ai-engine/models/` | `flower_pixel_hgb.joblib`, `species_gallery.json` + `.npz` (2.9 MB, the largest tracked file) |
| Simulator | `simulation/pollinex_sim/engine.py` | 6 modes |
| Frontend | `frontend/src/` | 19 page files covering 20 pages (`ModulePages.tsx` holds structure, maturity and health), Three.js simulator, camera scanner |
| Tests | `backend/tests`, `ai-engine/tests`, `simulation/tests`, `frontend/src/**/*.test.*`, `frontend/e2e` | see section 10 |
| Scripts | `scripts/` | `setup/run/test_windows.ps1`, bash equivalents, `check_dependencies.py` |
| CI | `.github/workflows/` | `ci.yml` (5 jobs, Ubuntu + Windows), `datasets.yml` (download and verification) |

## 3. Module audit (20 application modules / pages)

| # | Module (route) | Source | Works end to end | Tested | What is missing |
|---|---|---|:-:|---|---|
| 1 | Landing (`/`) | `Landing.tsx` | ✅ | E2E | — |
| 2 | Sign in / Register | `AuthPage.tsx`, `routers/auth.py` | ✅ | API + E2E | — |
| 3 | Dashboard (`/app`) | `Dashboard.tsx`, `analytics.py` | ✅ | API + E2E | — |
| 4 | Flower scanner | `Scanner.tsx`, `scans.py`, `/live/ws` | ✅ | API + E2E (fake camera) | Not yet tested on a real phone over HTTPS |
| 5 | Species recognition | `SpeciesPage.tsx`, `species.py` | ✅ | engine + API | 5 species have no reference images |
| 6 | Flower structure | `ModulePages.tsx`, `structure.py`, `regions.py` | 🟡 | engine unit | No anther/stigma labels, so there is no trained model |
| 7 | Maturity stages | `ModulePages.tsx`, `maturity.py` | 🟡 | engine unit | No stage labels, so it is a heuristic |
| 8 | Pollination readiness | `ReadinessPage.tsx`, `readiness.py` | ✅ (rules) | engine unit | No biological ground truth |
| 9 | Plant health | `ModulePages.tsx`, `health.py` | 🟡 | engine unit | Gives visual measurements only, by design |
| 10 | Virtual simulator | `Simulator.tsx`, `simulation/` | ✅ | 16 tests + E2E | Results are not field-validated |
| 11 | Environment | `EnvironmentPage.tsx`, `weather.py` | ✅ | API + engine | — |
| 12 | Field management | `FieldsPage.tsx`, `records.py` | ✅ | API | — |
| 13 | Flower inventory | `InventoryPage.tsx` | ✅ | API | — |
| 14 | Pollination history | `HistoryPage.tsx` | ✅ | API | — |
| 15 | Model evaluation | `EvaluationPage.tsx` | ✅ | E2E | **Updated:** now shows the sunflower extension and the cross-dataset detector result |
| 16 | Analytics | `AnalyticsPage.tsx` | ✅ | API | — |
| 17 | Research centre | `ResearchPage.tsx` | ✅ | E2E | — |
| 18 | Datasets | `DatasetsPage.tsx` | ✅ | E2E | **Updated:** now shows the `audited_not_used` and `unreachable` statuses |
| 19 | Reports (PDF/CSV/JSON) | `ReportsPage.tsx`, `reports.py` | ✅ | API | — |
| 20 | Admin settings | `AdminPage.tsx`, `admin.py` | ✅ | API (role checks) | — |

The 8 AI-engine modules in the master prompt:

| Module | Status |
|---|---|
| 1 Detection | ✅ trained and evaluated (USDA) |
| 2 Species | ✅ open-set gallery, evaluated |
| 3 Structures | 🟡 heuristic |
| 4 Maturity | 🟡 heuristic |
| 5 Readiness | ✅ rule engine |
| 6 Pose | 🟡 image-space heuristic |
| 7 Health | 🟡 heuristic |
| 8 Evaluation | ✅ |

## 4. Dataset source audit

From `datasets/dataset_sources.json`, also exported as `datasets/dataset_manifest.csv`.

| Dataset | Licence | Status | Images in repo | Annotation format | Notes |
|---|---|---|---|---|---|
| USDA Multi-species Fruit Flower (doi:10.15482/USDA.ADC/1423466) | CC BY 4.0 | ✅ integrated | 90 | PNG masks, plus YOLO boxes derived from mask components | Upstream boxes are vertically flipped, so they are not used. 117 unlabelled images are excluded. |
| TF Flower Detection (Zenodo 7768292) | CC BY 4.0 | ✅ integrated (sunflower subset) | 628 | YOLO, 1 class "flower" | 3,554 images downloaded, MD5 verified, all decoded, 2 exact duplicates removed. Only sunflower is committed. |
| TF `flower_photos` (Google) | CC-BY per image (Flickr) | ✅ used as the species label source | 0 (not committed) | class folders | 608 of the 628 committed images have a per-image Flickr attribution line in the subset's `LICENSE.txt`. The other 20 have no line in the upstream `flower_photos/LICENSE.txt` (the archive is published as CC-BY overall); remove those 20 if strict per-image attribution is required. |
| INESC Flower Detection (Zenodo 7708815) | CC BY 4.0 | audited, not used | 0 | YOLO, 1 class | Species unknown; 49 near-duplicate pairs cross its splits |
| Oxford 102 Flowers | not verified | **unreachable** | 0 | class labels only | Timed out from this workspace and from GitHub runners. The script is ready. |
| FlowerNet (Mendeley) | MIT | script only | 0 | class folders | Needs a manual download |
| EWD, DoPI, FloPE, PlantCLEF, structures, tomato candidates | various | documented or unverified | 0 | — | Reasons are given in the manifest |

## 5. Image inventory (actual files)

From `audit_datasets.py`, which walks every file, decodes each image and hashes it with SHA-1.

| Location | Images | Masks | Derived crops | Corrupt | Size |
|---|---|---|---|---|---|
| `processed/usda_fruit_flower` | 90 | 90 | 0 | 0 | 51.7 MB |
| `processed/tf_flower_detection_sunflower` | 628 | 0 | 0 | 0 | 26.7 MB |
| `processed/sunflower_gallery` | 0 | 0 | 628 | 0 | 9.4 MB |
| `reports` (figures) | — | — | — | 0 | 0.1 MB |

Other checks:

- Exact-duplicate groups: **0**
- Empty directories: `datasets/raw/` (originals are re-created by the scripts and are not committed)
- YOLO pairing: every image has a label file and every label file has an image (USDA 90/90; sunflower 439/439, 94/94 and 95/95)

## 6. Species verification (all nine)

| Species | Images | Annotated images | Boxes | Annotation type | Ready for training |
|---|---:|---:|---:|---|---|
| Apple | 48 | 48 | part of 4,651 | masks + derived boxes | ✅ detection and species |
| Peach | 24 | 24 | part of 4,651 | masks + derived boxes | ✅ detection and species |
| Pear | 18 | 18 | part of 4,651 | masks + derived boxes | ✅ detection and species |
| Sunflower | 628 | 628 | 2,432 | YOLO boxes (close-up photos) | ✅ species (done). Detection is ready to train but **not trained**. |
| Hibiscus | **0** | 0 | 0 | — | ❌ |
| Tomato | **0** | 0 | 0 | — | ❌ |
| Strawberry | **0** | 0 | 0 | — | ❌ |
| Brinjal | **0** | 0 | 0 | — | ❌ |
| Chilli | **0** | 0 | 0 | — | ❌ |

- **Anther, stigma, stamen and pistil annotations: 0 for every species.** None were generated.
- No classification images are used as detection labels, and no synthetic images exist in the dataset folders.

## 7. Dataset preparation and leakage control

- **USDA:** group-aware contiguous splits of 54 / 14 / 22 images:

  | Species | Train | Val | Test |
  |---|---:|---:|---:|
  | Apple | 29 | 7 | 12 |
  | Peach | 14 | 4 | 6 |
  | Pear | 11 | 3 | 4 |

  Boxes: 4,651 instances.
- **Sunflower:** split 439 / 94 / 95 images with 1,665 / 361 / 406 boxes. Gallery references come only from train and val (533). The 95 gallery test crops come only from the test split.
- Originals are preserved by the download scripts in `datasets/raw/`, which is git-ignored. The processed sets are committed with `data.yaml` (no absolute paths), split lists, licence and attribution.

## 8. Model and dataset consistency

| Model | Trained on | Genuinely supports | Held-out result |
|---|---|---|---|
| Pixel HGB detector (`flower_pixel_hgb.joblib`) | USDA, 54 train images | apple, peach, pear | test mAP@0.5 **0.410**, mAP@0.5:0.95 0.191 (22 images) |
| The same detector on sunflower test (no retraining) | — | **does not support sunflower** | mAP@0.5 **0.001**, recall@0.5 0.015, 95 images (`detector_on_tf_flower_detection_sunflower.json`) |
| Species gallery (`hcd-v1`, threshold 0.925, not re-tuned) | USDA, plus 533 sunflower references | apple, peach, pear, sunflower | sunflower recall **0.937** (89/95; 6 returned as unknown); apple/peach/pear flower accuracy after extension 0.934; USDA background rejected 0.482 |
| YOLO11 | — | not trained | — |

The sunflower gallery result is measured on close-up photos, not field photos. This addition **extends species coverage**. It
is not a claim that the existing detector improved.

## 9. Integration check

- The API (`/analytics/model-performance`) now also serves `species_extension_evaluation` and `detector_on_tf_flower_detection_sunflower`.
- The Evaluation page renders both reports.
- The gallery used by the scanner (`ai-engine/models/species_gallery.*`) now contains sunflower references. Its metadata records `extended_with: datasets/processed/sunflower_gallery`.
- The knowledge base, readiness rules and simulator modes cover all 9 species. Five of them are knowledge-only: they have no image references.

## 10. Testing status

| Suite | Count | Where run | Result |
|---|---:|---|---|
| AI engine (pytest) | 21 | this workspace (audit), CI Ubuntu + Windows | ✅ 21 passed |
| Simulator (pytest) | 16 | this workspace (audit), CI | ✅ 16 passed |
| Backend API (pytest) | 24 | CI Ubuntu + Windows | ✅ 24 passed (run 41644713098) |
| Frontend unit (Vitest) | 11 | CI | ✅ in CI |
| Playwright E2E | 14 | CI (Ubuntu) | ✅ in CI |
| Lint (`ruff --select F,E9,PLE`, the CI rule set) | — | this workspace | ✅ all checks passed |

- Backend, Vitest and E2E cannot run in this workspace because PyPI and npm are blocked. They run in GitHub Actions.
- The CI result for the audit commit is recorded in section 13.
- A broader `ruff check .` with the default rule set reports 215 style findings (formatting and simplification, not errors). These are not part of CI.

## 11. Repository hygiene

- **Secret scan** of all tracked files for AWS, GitHub, OpenAI and Slack tokens and private keys: **none found**. No `.env` file is tracked.
- **Largest tracked file:** 2.9 MB (`species_gallery.npz`). All dataset images are at most 1 MB each.
- **Committed datasets:** about 88 MB in total: USDA processed 52 MB, sunflower 27 MB, crops 9 MB.
- **Not committed (re-created by scripts):** raw archives (TF 220 MB, USDA about 6 GB) and the INESC download.
- **Git LFS:** not used. No single file is large enough to need it.

## 12. What is still missing

1. **Images for hibiscus, tomato, strawberry, brinjal and chilli.** No reachable, openly licensed source was found:
   - Oxford is unreachable.
   - The tomato-flower paper data is "available on request".
   - Roboflow and Kaggle cannot be reached from here.

   Next step: run `download_oxford102_subset.py` on a machine that can reach robots.ox.ac.uk (hibiscus), or collect the images and label them with the CVAT workflow in `datasets/annotation/`.
2. **Anther and stigma annotations** for any species.
3. **A detector trained on sunflower.** The data is ready (`processed/tf_flower_detection_sunflower`, YOLO format). Run `train_yolo11.py` on a GPU.
4. Field photos of sunflower for a field-condition species test.
5. A real-phone camera test over HTTPS, and a public deployment.

## 13. Changes in this audit and final state

**Changes:**

- New `audit_datasets.py` (full image inventory).
- `download_tf_flower_detection.py` now recovers species via the `flower_photos` join and exports the sunflower subset with attribution.
- New `download_inesc_flower_detection.py` and an Oxford mirror fallback.
- New `datasets.yml` workflow.
- New `extend_gallery.py` and `evaluate_detector_on.py`.
- Committed the USDA processed set (90 images) and the sunflower subset (628 images) plus gallery crops (628).
- Extended the species gallery with sunflower.
- Updated the dataset manifest (12 sources, honest statuses).
- API and Evaluation page now show the extension reports; the Datasets page shows the new statuses.
- README and dataset documentation updated with the verified counts.

**Final CI status** for audit commit `d434111`, [run 41644713098](https://github.com/nvaltryek-001/pollinex-ai/actions/runs/41644713098): all 5 jobs **succeeded**.

| Job | Result |
|---|---|
| Engine + simulator | 37 passed |
| Backend | 24 passed (SQLite and PostgreSQL migrations, startup) |
| Vitest | 11 passed |
| Type-check and production build | ✅ |
| Playwright E2E | 14 passed |
| Docker images | ✅ |
| Windows fresh-clone setup and tests | engine 37, backend 24, Vitest 11, Playwright 12 passed (2 screenshot tests skipped by design) |
