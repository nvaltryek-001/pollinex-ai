# POLLINEX AI: Final Release Report

_Report date: 2026-11-04. Repository: https://github.com/nvaltryek-001/pollinex-ai (branch `main`)._

Every number here comes from a committed report file or a test run named below. Nothing is estimated. "Not done" items are
listed in §8.

## 1. Summary
| Question | Answer (verified) |
|---|---|
| Real images in the repository | **1,479**: 718 with flower boxes (USDA 90, TF sunflower 628) + 761 iNaturalist photos with species labels only. 0 corrupt, 0 exact duplicates (`datasets/reports/dataset_inventory.md`). |
| Species with images | **9 of 9**, but strawberry (15), brinjal (20) and chilli (28) are too few to support. |
| Species the AI recognises (gallery) | **6 of 9**: apple, peach, pear, sunflower, hibiscus, tomato. Chosen by a validation gate fixed before any results existed. |
| Species the detector was trained on | **4 of 9**: apple, peach, pear, sunflower. No boxes exist for the other five. |
| Deployed detector | **YOLO11n (ONNX, CPU)**. USDA test mAP@0.5 **0.541** (previous pixel model 0.410); sunflower test mAP@0.5 **0.867** (pixel model 0.001). |
| Reproductive-structure, stage, health models | **Not trained.** 0 annotations exist. The modules remain labelled heuristics. |
| Tests | CI run 41764626714 on `ef89228`: all 5 jobs passed (details in §6). |

## 2. Datasets (actual files)
| Species | USDA (boxes) | TF sunflower (boxes) | iNaturalist (species label) | **Total** | iNaturalist licences |
|---|--:|--:|--:|--:|---|
| Apple | 48 | — | 107 | **155** | CC BY 67 · CC0 34 · BY-SA 6 |
| Peach | 24 | — | 71 | **95** | CC BY 55 · CC0 10 · BY-SA 6 |
| Pear | 18 | — | 29 | **47** | CC BY 23 · CC0 5 · BY-SA 1 |
| Sunflower | — | 628 | 200 | **828** | CC BY 158 · CC0 35 · BY-SA 7 |
| Hibiscus | — | — | 91 | **91** | CC BY 65 · CC0 14 · BY-SA 12 |
| Tomato | — | — | 200 | **200** | CC BY 154 · CC0 26 · BY-SA 20 |
| Strawberry | — | — | 15 | **15** | CC BY 9 · CC0 5 · BY-SA 1 |
| Brinjal | — | — | 20 | **20** | CC BY 17 · CC0 1 · BY-SA 2 |
| Chilli | — | — | 28 | **28** | CC BY 17 · CC0 10 · BY-SA 1 |
| **Total** | **90** | **628** | **761** | **1,479** | |

**Boxes:** USDA 4,651 boxes derived from masks; sunflower 2,432 YOLO boxes. The 628 derived sunflower crops are counted separately and are not in the total.

**iNaturalist verification** (`download_inat_flowering.py`, run 41665738978):
* **Species:** each observation is Research Grade, or cultivated with ≥ 1 agreeing and 0 disagreeing identifications.
* **Flowering:** each observation carries the annotation "Flowers and Fruits = Flowers".
* **Licence:** checked per photo. Only CC0, CC BY and CC BY-SA are kept; iNaturalist's default CC BY-NC is excluded.
* **Files:** all 761 files exist and decode, and all 761 have a non-empty attribution line in `ATTRIBUTION.csv`.
* **Splits:** by observer; 0 observers appear in more than one split.

**Why three crops have so few images:** strawberry, brinjal and chilli have few observations that carry *both* the flowering annotation *and* an open licence. Most iNaturalist photos are CC BY-NC.

**Unusable sources (§8):** Oxford 102 could not be reached; the INESC set was rejected for unknown species and split leakage.

## 3. Models
### 3.1 Flower detector: YOLO11n (deployed)

**Training run.** GitHub Actions run 41663935349, CPU only, finished 2026-11-03 18:56 UTC, conclusion **success**:
* 97 epochs within a 4-hour cap, 800 px, from COCO-pretrained `yolo11n.pt`
* `best.pt` chosen on validation (val mAP@0.5 0.728)
* exported to ONNX at `ai-engine/models/flower_yolo11n.onnx` (sha256 `f5e05cf8…af0b3`, 10.8 MB), with sidecar `flower_yolo11n.json` (imgsz 800)

**Deploy rule.** Written before training (`yolo_deploy_rule.py`): deploy only if USDA-test mAP@0.5 is at least the pixel model's, using the same evaluation code. 0.541 ≥ 0.410, so it was deployed.

**Independent test sets**, never used for training or selection:

| Test set | Model | mAP@0.5 | mAP@0.5:0.95 | Precision@0.5 | Recall@0.5 | F1@0.5 |
|---|---|--:|--:|--:|--:|--:|
| USDA apple/peach/pear (22 images, 929 flowers) | pixel (previous) | 0.410 | 0.190 | 0.169 | 0.610 | 0.265 |
| | **YOLO11n** | **0.541** | **0.277** | 0.265 | 0.746 | 0.391 |
| TF sunflower (95 images, 406 flowers) | pixel | 0.001 | 0.001 | 0.001 | 0.015 | 0.002 |
| | **YOLO11n** | **0.867** | **0.682** | 0.543 | 0.921 | 0.683 |

**Local check of the exported model.** I re-ran `evaluate_detector_on.py` with the committed ONNX file in this workspace (onnxruntime 1.29). It reproduced exactly: USDA 0.541 / 0.277, sunflower 0.867 / 0.682, with 0 images without predictions. Mean latency was 151 ms per image locally and 34 ms on the GitHub runner (pixel model 910 ms).

**End-to-end check.** The `Analyzer` loads `yolo11-onnx` by default. On a sunflower test image it gave 10 detections, 9 labelled sunflower.

**Limitations:**
* Precision on cluttered orchard scenes is still low (0.265).
* Count errors are large at the 0.05 evaluation threshold.
* Detection on the five crops without boxes is unvalidated.
* **Licence:** Ultralytics YOLO11 is AGPL-3.0 (`ai-engine/models/YOLO11_LICENSE_NOTE.md`). Deleting the `.onnx` restores the MIT pixel model.

### 3.2 Species recognition: open-set gallery (deployed)
Built by `build_species_gallery_multi.py`; report in `reports/species_multi_evaluation.json`.
* **Embedding:** chosen on validation by macro-F1. ImageNet MobileNetV3-Large features (`mnv3l-v1`, ONNX, BSD-3 weights, not fine-tuned) scored 0.586; the hand-crafted `hcd-v1` scored 0.442. Threshold 0.6375.
* **Gate** (fixed in advance): ≥ 50 references and validation recall and precision ≥ 0.50.
  * **Enabled:** apple, peach, pear, sunflower, hibiscus, tomato.
  * **Not enabled:** strawberry (10 references), brinjal (15), chilli (25).
* **Test** (used once): accuracy **0.746**, macro-F1 **0.727**.

| Class | Precision | Recall | F1 | Test support |
|---|--:|--:|--:|--:|
| apple | 0.722 | 0.948 | 0.820 | 403 |
| peach | 0.695 | 0.892 | 0.781 | 158 |
| pear | 0.757 | 0.848 | 0.800 | 165 |
| sunflower | 0.958 | 0.906 | 0.931 | 127 |
| tomato | 0.906 | 0.853 | 0.879 | 34 |
| hibiscus | 0.714 | 0.714 | 0.714 | **7** (very small) |
| unknown (background) | 0.524 | **0.098** | 0.165 | 224 |

Confusion matrix (rows = truth; columns apple, hibiscus, peach, pear, sunflower, tomato, unknown):

```
apple      382   0   7   9   0   1   4
hibiscus     0   5   1   0   1   0   0
peach        2   0 141   7   2   0   6
pear        20   0   5 140   0   0   0
sunflower    1   2   1   0 115   2   6
tomato       0   0   0   0   1  29   4
unknown    124   0  48  29   1   0  22
```

**By source:**

| Test set | Images | Accuracy |
|---|--:|--:|
| USDA orchard crops | 694 | 0.927 |
| iNaturalist field photos | 109 | 0.716 |
| Sunflower close-ups | 95 | 0.968 |
| USDA background (rejected as unknown) | 220 | **0.095** |

**Known regression:** background rejection fell from 0.468 (hcd-v1) to 0.095. Validation showed the same weakness before test was run. False detections are therefore usually given a species, so prefer **Close-up** mode for single flowers.

### 3.3 Heuristic modules (unchanged scope, honestly labelled)
* **Maturity, structures and pose:** heuristics, with no labels to validate them.
* **Health:** indicators are now grouped as discoloration, wilting, petal damage and visible abnormality. They are not validated and never name a disease.
* **Readiness:** species-specific rules using maturity, visible-region measurements and environment, with confidence and uncertainty. No biological ground truth exists.

## 4. Annotation workflow (Phase 3)
* **Schema:** `datasets/annotation/cvat_labels.json`:
  * `flower` box, with attributes species, stage (bud … senescent, plus `uncertain`), occluded, truncated and style class
  * `flower_centre` point
  * polygons for `petal`, `anther`, `stigma`, `stamen`, `pistil` and `health_issue`
* **Guidelines:** `ANNOTATION_GUIDELINES.md`, with class and stage definitions, visibility-only rules, 20 % second-annotator review, and splits by capture session.
* **Tool:** `datasets/scripts/annotation_stats.py`:
  * statistics for the committed data (`datasets/reports/annotation_statistics.md`)
  * CVAT-COCO validation
  * COCO → YOLO conversion for the flower and structure sets
  * covered by 3 unit tests
* **Current counts:** 0 annotations for every structure, centre, stage and health class. None were generated.

## 5. Integration
* **Backend:** loads the ONNX detector automatically (image size from the sidecar) and the gallery with its embedding.
* **`/analytics/model-performance`** serves `yolo11_deploy_decision`, `species_multi_evaluation` and the earlier reports.
* **Dashboard and PDF report** show the deployed YOLO11 metrics.
* **Evaluation page** shows:
  * a "Deployed detector: YOLO11n" card and a detector comparison table
  * the 9-species gating table and confusion matrix
  * the pixel model, labelled as the fallback
* **Health page** shows indicator categories. The Datasets page shows the new dataset statuses.

## 6. Tests
**CI run [41764626714](https://github.com/nvaltryek-001/pollinex-ai/actions/runs/41764626714)** on `ef89228`, the first commit with YOLO11 deployed: all 5 jobs **succeeded**.

| Job | Result |
|---|---|
| AI engine + simulator | **43 passed**: 27 engine, including the deployed-ONNX test and the gating test, plus 16 simulator |
| Backend | **24 passed** (SQLite and PostgreSQL migrations, startup) |
| Frontend unit (Vitest) | **11 passed** |
| Type-check and production build | ✅ |
| Playwright E2E, desktop + mobile, fake camera | **14 passed** |
| Docker images | ✅ |
| Windows fresh clone (`setup_windows.ps1`, `test_windows.ps1 -E2E`) | engine 43, backend 24, Vitest 11, Playwright 12 passed; 2 screenshot tests skipped by design |

Run locally in this workspace: AI engine 27 passed, simulator 16 passed, `ruff --select F,E9,PLE` clean. The docs-only commit after `ef89228` is checked by its own CI run, linked from the commit history.

## 7. Reproduce
```bash
python datasets/scripts/download_inat_flowering.py --per-species 200          # or workflow .github/workflows/inat.yml
python ai-engine/training/build_species_gallery_multi.py --save
python ai-engine/training/train_yolo11.py --combined --imgsz 800 --time 4 --device cpu   # or .github/workflows/yolo.yml
python ai-engine/training/evaluate_detector_on.py --data datasets/processed/usda_fruit_flower --split test --detector onnx:ai-engine/models/flower_yolo11n.onnx
python ai-engine/training/yolo_deploy_rule.py
```
GPU: `notebooks/train_yolo11_colab.ipynb`. It runs the same training and evaluation as the CPU workflow, with the same deploy rule, at 1280 px.

## 8. Not done / limitations (truthful)
1. **Strawberry, brinjal and chilli are not AI-supported.** They have 15, 20 and 28 openly licensed images, below the gate. More photos are needed: own photos via CVAT, or licence-compatible sources.
2. **No boxes for hibiscus, tomato, strawberry, brinjal or chilli**, so the detector is not trained or validated on them.
3. **No anther, stigma, stamen, pistil, petal, stage or health annotations**, so these modules remain heuristics.
4. **Small test sets** for hibiscus (7 iNaturalist test images) and brinjal, chilli and strawberry (1–2 each).
5. **Background rejection** of the deployed gallery is weak (0.095).
6. **Licensing:**
   * YOLO11 model: AGPL-3.0.
   * 56 iNaturalist photos are CC BY-SA, and the gallery embeddings derived from them carry that licence.
   * 20 of the 628 TF sunflower images have no per-image Flickr attribution upstream.
7. **Oxford 102 could not be reached** from the workspace or from GitHub runners.
8. **Not done:** phone camera test over HTTPS, and public deployment.
