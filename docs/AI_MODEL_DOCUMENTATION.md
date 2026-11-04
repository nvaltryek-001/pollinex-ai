# AI Model Documentation

## Model choice
**Deployed detector (2026-11-04): YOLO11n, exported to ONNX** (`models/flower_yolo11n.onnx`, 10.8 MB, input 800 px, one class `flower`).
It runs on CPU with onnxruntime. The earlier pixel boosted-trees model is kept as the MIT-licensed fallback and is used automatically
when the ONNX file is absent.

| Candidate | Licence | Decision |
|---|---|---|
| **Ultralytics YOLO11n** | AGPL-3.0 | **deployed.** Trained on CPU in GitHub Actions; passed the deploy rule |
| Pixel boosted trees + watershed | BSD (scikit-learn) | fallback (MIT-compatible) |
| YOLOv8 | AGPL-3.0 | superseded by YOLO11 in the same package |
| RT-DETR | Apache-2.0 / AGPL in Ultralytics | not tried (CPU budget) |

### Module 1a · YOLO11n (`training/train_yolo11.py`, `.github/workflows/yolo.yml`)

**Data.** Built by `--combined`: USDA apple/peach/pear boxes plus TF Flower Detection sunflower boxes, one class. Each source keeps its own split:

| Split | USDA | Sunflower |
|---|--:|--:|
| Train | 54 | 439 |
| Val | 14 | 94 |
| Test | 22 | 95 |

**Training.** COCO-pretrained `yolo11n.pt` with Ultralytics defaults, plus:
* image size 800, batch 16, seed 20261102, deterministic, patience 15, `close_mosaic=5`
* a 4-hour time cap; 97 epochs completed
* CPU on a GitHub runner, run 41663935349, finished 2026-11-03
* `best.pt` chosen on validation fitness (val mAP@0.5 0.728)

**Pre-registered deploy rule** (`training/yolo_deploy_rule.py`, written before training): deploy only if USDA-test mAP@0.5 is at
least the pixel model's, measured with the same evaluation code (`evaluate_detector_on.py`). Result: 0.541 ≥ 0.410, so **deployed**.

**Held-out test results** (`reports/yolo11_deploy_decision.json`, re-run locally from the committed ONNX with identical numbers):

| Test set | mAP@0.5 | mAP@0.5:0.95 | P@0.5 | R@0.5 | F1@0.5 |
|---|--:|--:|--:|--:|--:|
| USDA (22 images, 929 flowers) | 0.541 | 0.277 | 0.265 | 0.746 | 0.391 |
| Sunflower (95 images, 406 flowers) | 0.867 | 0.682 | 0.543 | 0.921 | 0.683 |

The pixel model scores 0.410 / 0.190 on USDA and 0.001 on sunflower under the same protocol.

**Speed and counting.**
* Mean latency is 34 ms per USDA image on the GitHub runner and about 150 ms in this workspace (pixel model 910 ms on the runner).
* Count errors are large at the evaluation threshold of 0.05: USDA count MAE 77 against MAE 110 for the pixel model.

**Limitations.**
* No boxes exist for hibiscus, tomato, strawberry, brinjal or chilli, so detection on those crops is unvalidated.
* On a tomato field photo, detections were labelled apple or pear by the species gallery. The gallery's tomato references are whole-scene photos, not crops. Use **Close-up** mode for single flowers.

**Licence.** AGPL-3.0; see `models/YOLO11_LICENSE_NOTE.md`.

## Module 1b · Pixel detector (fallback; `pollinex_ai/detector.py`)
* **Features** (`features.py`, version `pfx-v1`): RGB, Lab a/b, L, hue-as-vector × saturation, saturation, value, whiteness
  (V·(1−S)), excess-green; for σ ∈ {1,2,4}: smoothed a, b, L, whiteness, ExG, gradient magnitude, σ²-normalised LoG, local std.
  36 channels.
* **Classifier**: `HistGradientBoostingClassifier(max_iter=250, max_leaf_nodes=63, lr=0.1, l2=1.0)`, 486k training pixels.
* **Post-processing**: threshold 0.6, opening, hole filling, connected components (watershed disabled: tuned `peak_distance=0`),
  min area 30 px at 1280 px work size. Score = mean probability in the instance. `low_confidence` if < 0.6.
* **Inference**: 1280 px, pixel stride 2 (bilinear upsampling) — 4.7× faster than stride 1 with equal validation mAP;
  live mode 800 px.
* **File**: `models/flower_pixel_hgb.joblib` (≈0.8 MB, scikit-learn 1.9.1; joblib/pickle — load only trusted files).

### Results (test split, 22 images, 929 instances)
See README table. Deployed config: **mAP50 0.410, mAP50-95 0.191**, P 0.169, R 0.610. Baseline Otsu 0.127; colour-only 0.240.

### Error analysis
* Recall by size: < 16 px 0.47, 16–40 px 0.64, > 40 px 0.75.
* Main false-positive sources (overlay figures in `reports/figures/`): pale bark and branch highlights; distant, unlabelled
  blossoms on background trees; specular grass.
* Hardest test images are those with large background tree areas (e.g. `apple_IMG_0380`, `pear_2_47`).
* A shape filter (aspect ratio / fill) was explored on **validation only** and gave +0.003 mAP50 — not adopted.
* Next steps: YOLO11 at 1280 px on the same splits; bark hard-negative mining; tiling (Schouten et al.).

## Module 2 · Species gallery (`species.py`, `training/build_species_gallery_multi.py`)
**Deployed (2026-11-04, gallery v2):** embedding `mnv3l-v1` (ImageNet MobileNetV3-Large, ONNX, BSD-3, not fine-tuned), kNN with k = 7, open-set threshold 0.30, plus **540 background references**. The background references are real non-flower crops from the USDA **train** masks; a background match returns `unknown`.

**Pre-registered variant choice on validation** (2 embeddings × background on/off × balancing at 300 references on/off):

| Variant | Val macro-F1 | Val unknown recall |
|---|--:|--:|
| hcd-v1, no background | 0.497 | 0.29 |
| hcd-v1, background, balanced | 0.583 | 0.75 |
| mnv3l-v1, no background (previous deployed setup) | 0.758 | 0.24 |
| **mnv3l-v1, background (deployed)** | **0.832** | 0.67 |
| mnv3l-v1, background, balanced | 0.810 | 0.81 |

**References** (training splits only):

| Source | References |
|---|---|
| USDA crops | apple 888 · peach 491 · pear 424 |
| TF sunflower close-ups | 533 |
| iNaturalist and Commons | apple 67 · peach 52 · pear 18 · sunflower 142 · hibiscus 204 · tomato 230 · brinjal 109 · chilli 66 · strawberry 31 |

**Gate:** ≥ 50 references and validation recall and precision ≥ 0.50.
* **Enabled:** apple, peach, pear, sunflower, hibiscus, tomato, brinjal and chilli.
* **Not enabled:** strawberry (31 references; validation recall 0.43).

**Support status** is shown on every result: `validated` with ≥ 20 test images, otherwise `limited_evidence`. Brinjal (11) and chilli (7) are limited evidence.

**`uncertain`** is set when the top vote share is below 0.60 (a fixed rule, not tuned).

**Test**, used once: accuracy **0.874**, macro-F1 **0.862**.

| Class | P | R | F1 | n |
|---|--:|--:|--:|--:|
| apple | 0.851 | 0.933 | 0.890 | 403 |
| brinjal | 0.667 | 0.909 | 0.769 | 11 |
| chilli | 1.000 | 0.714 | 0.833 | 7 |
| hibiscus | 0.778 | 0.913 | 0.840 | 23 |
| peach | 0.848 | 0.918 | 0.881 | 158 |
| pear | 0.855 | 0.855 | 0.855 | 165 |
| sunflower | 0.952 | 0.937 | 0.944 | 126 |
| tomato | 0.925 | 0.984 | 0.954 | 63 |
| unknown | 0.934 | 0.686 | 0.791 | 226 |

**By source:**

| Test set | Images | Accuracy |
|---|--:|--:|
| USDA crops | 694 | 0.924 |
| USDA background | 220 | 0.705 |
| Sunflower close-ups | 94 | 0.979 |
| iNaturalist | 109 | 0.798 |
| Commons | 65 | 0.892 |

**Strawberry** test photos are assigned other species (brinjal ×3, sunflower, apple, tomato), not `unknown`.

**Confusion matrix** (rows = truth; columns apple, brinjal, chilli, hibiscus, peach, pear, sunflower, tomato, unknown):
```
apple      376  0  0  1   8   9   0  0   9
brinjal      0 10  0  1   0   0   0  0   0
chilli       0  2  5  0   0   0   0  0   0
hibiscus     0  0  0 21   0   0   1  1   0
peach        1  0  0  2 145   7   3  0   0
pear        19  0  0  0   4 141   0  0   1
sunflower    1  0  0  2   1   0 118  3   1
tomato       0  0  0  0   0   0   1 62   0
unknown     45  3  0  0  13   8   1  1 155
```
**Caveats:**
* The threshold of 0.30 is at the bottom of the swept range. With background references, rejection is done mostly by the background class rather than the threshold.
* iNaturalist and Commons photos are evaluated as centre crops of whole scenes. In the app, **Close-up** mode uses exactly that crop.

## Module 3 · Structure-model hook
`structure.apply_structure_model` loads `models/structures_yolo.onnx` (+ `.json` with class names) when it exists. It then sets
each covered class (anther, stigma, stamen, pistil, petal) to `trained_model`, with detections. Classes it does not cover stay
`not_ai_validated`. The hook is unit-tested with a stand-in model. **No structure model exists yet**, because 0 structure annotations exist.
Workflow: `datasets/annotation/make_annotation_batch.py` → CVAT → `annotation_stats.py --coco --to-yolo` → `train_yolo11.py`.

## Modules 3, 4, 6, 7 · Heuristics
| Module | Method | Output flag |
|---|---|---|
| Centre / structures | Lab distance from the median petal colour within 0.45·r of the centroid; yellow-pixel fraction | `structure_detection_available: false` |
| Maturity | Softmax over interpretable scores from fill, solidity, elongation, radial lobing, colour fractions (green/brown/white/yellow/dark) | `method: heuristic, validated: false` |
| Pose | Image moments → centroid, major-axis angle, facing ratio √(λ2/λ1); alignment vector to a virtual effector | `coordinate_space: image` |
| Health | Brown fraction, dark-spot blobs, hue-saturation discolouration, outline solidity vs. thresholds | never names a disease |
Flower masks come from the detector probability map, or (close-ups) from a border-colour background model with GrabCut fallback.

## Module 5 · Readiness rule engine (`readiness.py`)
Inputs: species KB entry, stage + score, centre cues, health indicators, environment. Category from
`ready/approaching/past_stages`; browning on a "ready" flower → `past_window`; unknown species → `indeterminate` with no strategy.
Confidence = stage score × detection score × species confidence × 0.8 per unfavourable environmental factor.

## Module 8 · Evaluation code (`metrics.py`)
COCO-style greedy matching, 101-point interpolated AP, IoU thresholds 0.50:0.05:0.95; precision/recall/F1 reported at the
lowest score (all predictions); counting MAE/MAPE; pixel IoU/F1; classification confusion matrix. Unit-tested.

## Reproduce
```bash
python ai-engine/training/train_detector.py          # writes models/flower_pixel_hgb.joblib + reports/detector_evaluation.json
python ai-engine/training/evaluate_detector.py       # reports/detector_inference_tradeoff.json, sets stride/fast_side
python ai-engine/training/train_species.py           # models/species_gallery.* + reports/species_evaluation.json
python ai-engine/training/train_yolo11.py --data datasets/processed/usda_fruit_flower/data.yaml   # optional, needs PyTorch
```

## Optional GPU training on Google Colab (YOLO11)
Ready-made notebook: [`notebooks/train_yolo11_colab.ipynb`](../notebooks/train_yolo11_colab.ipynb). It trains on the same combined data, and evaluates with the same code and deploy rule, as the CPU workflow `.github/workflows/yolo.yml`. Its numbers are new results; report them only from `ai-engine/reports/`. The manual steps below are the older USDA-only route.

1. Colab → *Runtime → Change runtime type → T4 GPU*.
2. In a cell:
   ```bash
   !git clone https://github.com/nvaltryek-001/pollinex-ai.git
   %cd pollinex-ai
   !pip -q install -r ai-engine/requirements-train.txt opencv-python-headless scikit-image scikit-learn==1.9.1 joblib
   !GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://github.com/ai-agriculture-circuits-and-systems/multi-species-fruit-flower /content/mff
   !python datasets/scripts/prepare_usda_fruit_flower.py --src /content/mff      # same splits as the CPU model
   !python ai-engine/training/train_yolo11.py --data datasets/processed/usda_fruit_flower/data.yaml --epochs 100 --imgsz 1280 --batch 8 --device 0
   ```
3. Download `ai-engine/models/flower_yolo11n.onnx` and `ai-engine/reports/yolo11_evaluation.json`
   (`from google.colab import files; files.download(...)`), copy both into the same paths on your laptop and press
   *Admin settings → Reload from disk*. The backend now uses the ONNX detector on CPU; the evaluation page shows its report.
4. Compare it with the CPU baseline on the **same test split**; update the README only with the measured values.

Licence reminder: Ultralytics YOLO11 is AGPL-3.0.

## Model configuration files
Every trained artefact stores its configuration next to its metrics: `models/flower_pixel_hgb.joblib → params`
(threshold, min_area, peak_distance, work_side, stride, fast_side, version, training data), `models/species_gallery.json`
(k, threshold, embedding version, sources) and the `params`/`seed` blocks in each `reports/*.json`.

## Reproducible evaluation of the deployed models
`python scripts/evaluate_deployed_models.py` loads the shipped detector and gallery and evaluates them on the held-out test splits.
Detection results and classification results are written to separate sections of
[`MODEL_EVALUATION_RESULTS.md`](MODEL_EVALUATION_RESULTS.md). The 2026-11-04 run reproduced the committed numbers exactly:

| Detection | P@0.5 (deployed thr. 0.30) | R@0.5 (0.30) | mAP@0.5 | mAP@0.5:0.95 |
|---|--:|--:|--:|--:|
| USDA apple/peach/pear | 0.647 | 0.578 | 0.593 | 0.332 |
| TF sunflower | 0.817 | 0.837 | 0.871 | 0.694 |

Species classification: 1,182 test items, accuracy 0.874, macro-F1 0.862.

No model predicts fruit, disease, pollen viability or reproductive structures.

## What is trained, what is rule-based, what is simulated
| Kind | Components |
|---|---|
| **Trained AI** | YOLO11n flower detector (one class, `flower`, trained on apple/peach/pear/sunflower boxes); species reference gallery (MobileNetV3 embeddings + k-NN, 8 species enabled, background references for *unknown*) |
| **Rule-based / heuristic** | developmental stage, centre region (pollen-like cluster), visible health indicators, pose, pollination readiness |
| **Simulation** | virtual pollen-transfer simulator (seeded particle model) |

The detector has a single `flower` class. It does not predict species, and it has no boxes for hibiscus, tomato, strawberry, brinjal or chilli.

## End-to-end check on real photos of all nine species
`scripts/sample_inference_check.py` runs the full pipeline on the first 5 held-out iNaturalist/Commons test photos per species.
This is a smoke check, not a metric. On 2026-11-04 the top flower's species matched the photo label as follows:

| Mode | apple | peach | pear | sunflower | hibiscus | tomato | brinjal | chilli | strawberry (not supported) | 8 supported species |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| close-up | 4/5 | 3/5 | 2/5 | 4/5 | 4/5 | 5/5 | 4/5 | 3/5 | 0/5 | **29/40** |
| auto | 3/5 | 1/5 | 1/5 | 4/5 | 4/5 | 3/5 | 2/5 | 3/5 | 0/5 | **24/40** |

**Finding:** auto mode classifies the crop of the top detection box, which is often smaller or off-centre in whole-scene
photos. Close-up mode classifies the whole frame, which matches how the gallery was built and evaluated (centre crop). For a
single flower, use close-up mode. Strawberry was never returned as *unknown*. Its photos were assigned to other species,
which is a known weakness of the open-set rejection.
