# Release checklist: final completion phase

_Started 2026-11-03 from commit `444a2ae`. ✅ = done and verified · 🟡 = done with stated limits · ❌ = blocked (reason given).
Final numbers are in `docs/FINAL_PROJECT_AND_DATASET_AUDIT.md`. This list is kept in sync with it._

## Phase 1: issues found by the repository audit
| # | Issue (as found at `444a2ae`) | Resolution |
|---|---|---|
| 1 | 5 of 9 species (hibiscus, tomato, strawberry, brinjal, chilli) had **0 images** | 🟡 iNaturalist flowering photos, species-verified and openly licensed (see Phase 2). Counts vary by species. |
| 2 | Species gallery covered 4 species with no rule for when a species counts as "supported" | ✅ `build_species_gallery_multi.py` applies a gating rule that was written before any results existed and is decided on validation data. The test split is used once. |
| 3 | YOLO11 recipe was never run | ✅ `.github/workflows/yolo.yml` trains it on CPU with the same evaluation code as the existing detector. A deploy rule, also written before any results, decides whether it replaces the existing detector. |
| 4 | The existing detector cannot find sunflowers (mAP@0.5 0.001) | Addressed by the YOLO11 run on USDA + sunflower boxes (result in audit §8). |
| 5 | Annotation schema had only flower, anther_region and stigma | ✅ Full CVAT schema: flower box (with species and stage attributes), centre point, petal, anther, stigma, stamen, pistil and health_issue, plus class definitions. |
| 6 | No annotation statistics or QA tool | ✅ `annotation_stats.py`: per-dataset and per-species statistics, CVAT-COCO validation and conversion to YOLO with splits by capture session. Unit-tested. |
| 7 | No Colab notebook | ✅ `notebooks/train_yolo11_colab.ipynb` |
| 8 | Health module had no wilting category, and its indicators were not grouped | ✅ Indicators are grouped into discoloration, wilting, petal damage and visible abnormality. The wilting indicator is a heuristic. |
| 9 | ONNX detector ignored its export size | ✅ The loader reads the `flower_yolo11n.json` sidecar for image size and class names. |
| 10 | The cross-dataset evaluator only handled one dataset layout | ✅ It now supports both layouts and can evaluate any chosen detector. |

## Blocked or not possible with available data
- **Anther, stigma, stamen, pistil and petal models:** ❌ no annotations exist (0 of every class). The workflow is ready; no labels are generated.
- **Trained maturity-stage model:** ❌ no stage labels exist. The stage stays a heuristic.
- **Trained health model:** ❌ no health labels exist. The indicators stay heuristics.
- **Bounding boxes for the 5 new species:** ❌ iNaturalist gives image-level species labels only. They are never used as detection labels.
