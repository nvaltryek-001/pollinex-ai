# Model cards

Every number below comes from a committed report in `ai-engine/reports/`. Each card names its report file, and
`scripts/evaluate_deployed_models.py` reproduces the headline metrics.

---

## 1. Flower detector: `flower_yolo11n` (deployed)

| | |
|---|---|
| Task | Flower localisation: one class, `flower`. **It does not predict species.** |
| Architecture | Ultralytics YOLO11n, ONNX export, CPU inference at 960 px. Operating confidence 0.30, chosen on validation; detections down to 0.15 are kept and flagged `low_confidence`. |
| Training data | USDA Multi-species Fruit Flower (apple, peach, pear; CC BY 4.0) and the TF Flower Detection sunflower subset (CC BY 4.0): 718 images, about 7,000 boxes. Grouped splits; 1 near-duplicate test image excluded. |
| Training | 64 epochs on a GitHub Actions CPU runner. The checkpoint was chosen on validation, and the model was deployed under a deploy rule fixed before training (`yolo_select_rule.py`, `yolo_deploy_rule.py`). |
| Test results | USDA: mAP@0.5 **0.593**, mAP@0.5:0.95 0.332, P/R at the 0.30 threshold 0.647/0.578. Sunflower: mAP@0.5 **0.871**, mAP@0.5:0.95 0.694, P/R 0.817/0.837. Per species mAP@0.5: apple 0.602, peach 0.568, pear 0.609. |
| ONNX vs PyTorch | 85.5 % of boxes match at IoU ≥ 0.8 (`yolo11_onnx_consistency.json`). |
| Not evaluated | Hibiscus, tomato, strawberry, brinjal and chilli: no boxes exist for them, so no detection performance is claimed. |
| Known failure modes | Small, occluded or back-lit flowers. Dense orchard clusters, where precision is low at low thresholds. |
| Licence | AGPL-3.0, because it was trained with Ultralytics. Delete the file and the MIT pixel detector is used instead. |
| Reports | `yolo11_evaluation.json`, `yolo11_deploy_decision.json`, `deployed_model_evaluation.json` |

## 2. Fallback detector: `pixel-hgb-20261102`

A pixel classifier (histogram gradient boosting on colour and texture features) with connected components. It is MIT
licensed, and it is used automatically when the ONNX model or `onnxruntime` is missing. USDA test mAP@0.5 is 0.410, and it
scores 0.001 on sunflower (`detector_evaluation.json`).

## 3. Species recognition: reference gallery `mnv3l-v1` (deployed)

| | |
|---|---|
| Task | Open-set species of a flower crop. It answers one of 8 species or **unknown**. |
| Architecture | ImageNet MobileNetV3-Large embeddings (torchvision weights, BSD-3; ONNX; 960-d) plus a k-NN vote (k = 7) over labelled reference crops. Reference labels that are never returned: 540 USDA background crops, and 31 strawberry photos used only for rejection. |
| References | apple 955, peach 543, pear 442, sunflower 675, hibiscus 204, tomato 230, brinjal 109, chilli 66. The sources are USDA crops, TF sunflower close-ups, and the train splits of iNaturalist and Commons. |
| Support status | Validated (≥ 20 test images): apple, peach, pear, sunflower, hibiscus, tomato. Limited evidence: brinjal (11), chilli (7). Not supported: strawberry, which failed the gate fixed before results existed (≥ 50 references, val P and R ≥ 0.5). |
| Test, crops / close-ups | 1,182 items: accuracy **0.878**, macro-F1 **0.882**. The confusion matrix is in `MODEL_EVALUATION_RESULTS.md`. |
| Whole-photo pipeline, test | Top flower per photo, with the crop/scene blend (crop weight 0.25) and strawberry rejection references, both chosen on validation. Auto mode: accuracy **0.832**, macro-F1 **0.778**, strawberry → unknown 4/6. Close-up mode: accuracy 0.784, macro-F1 0.702 (`species_unsupported_rule.json`). |
| Rejected options | Abstaining below a vote-share threshold lowered validation macro-F1 at every threshold, so it is not used (`species_context_rule.json`). |
| Known failure modes | 30 % of orchard background crops still receive a species. Apple, peach and pear are confused with each other. Brinjal and chilli have few test images. |

## 4. Not models: heuristics and rules

| Component | Method | Notes |
|---|---|---|
| Developmental stage | Colour and shape heuristic | No stage annotations exist; the result shows a distribution and an `uncertain` flag. |
| Centre region / structures | Colour heuristic | Anther, stigma, stamen, pistil and sepal are listed as `not_ai_validated`. A trained structure model slots in automatically once one exists (`structure.py`). |
| Visible health | Colour-anomaly measurements | Never names a disease. |
| Pose | Image-space geometry | Not a real-world distance. |
| Pollination readiness | Species-specific rule engine | A visual estimate. It does not prove pollen viability, stigma receptivity or fertilisation. |
| Simulator | Seeded particle simulation | Computation, not measurement. |

## 5. Pending models

| Model | Status | What it needs |
|---|---|---|
| Nine-class species-aware detector | `pending_verified_annotations` (`species_detector_status.json`) | Human-verified boxes: at least 50 train, 15 val and 15 test images per class. There are proposals for 1,267 photos, and none are reviewed yet. |
| Reproductive-structure detector | Pending, with 0 annotations | CVAT labels: anther, stigma, stamen, pistil, petal, sepal. |
| Stage classifier | Pending, with 0 annotations | The `stage` attribute on reviewed `flower` boxes. |
| Fruit recognition | No dataset | See `SPECIES_KNOWLEDGE_BASE.md`. |
