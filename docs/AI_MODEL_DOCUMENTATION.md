# AI Model Documentation

## Model choice (and why not a deep detector — yet)
The specification asked to investigate YOLOv8, YOLO11 and RT-DETR and to choose by reproducible experiment, compute budget,
licence and available annotations. Constraints in the build environment: 2 vCPU, no GPU, and **no access to PyPI** (PyTorch and
Ultralytics could not be installed). The deployed detector is therefore a CPU model trained from scratch with
scikit-learn; a YOLO11 recipe (`ai-engine/training/train_yolo11.py`) and an ONNX runtime backend are provided so the deep model
can be trained on any machine with PyTorch and dropped in without code changes.

| Candidate | Licence | Needs | Decision |
|---|---|---|---|
| Ultralytics YOLO11-n | AGPL-3.0 | PyTorch; GPU recommended | recipe + ONNX backend shipped; not trained here |
| YOLOv8 | AGPL-3.0 | same | superseded by YOLO11 in the same package |
| RT-DETR | Apache-2.0 (paper code) / AGPL in Ultralytics | heavier training | rejected for laptop budget |
| **Pixel boosted trees + watershed** | BSD (scikit-learn) | CPU only | **deployed** |

## Module 1 · Flower detector (`pollinex_ai/detector.py`)
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

## Module 2 · Species gallery (`species.py`)
* Embedding `hcd-v1`: 12×4×4 HSV histogram, Lab mean/std, centre-minus-ring Lab difference, HOG (9 orientations, 16-px cells),
  10-bin uniform LBP; weighted and L2-normalised (≈ 380 dims).
* kNN (k=7) cosine vote; open-set threshold **0.925** (validation macro-F1 0.783).
* Gallery: 1,803 crops (apple 888 · peach 491 · pear 424). Stored as `.npz` + `.json` (no pickle).
* Test: open-set accuracy 0.819, macro-F1 0.799 (apple 0.887, peach 0.849, pear 0.886, unknown 0.575); background rejection 0.468;
  leave-one-species-out unknown rate apple 0.435, peach 0.919, pear 0.219.
* **Confound**: species ↔ camera setup. **Unknown handling** works but is imperfect (pear crops of an unseen species are often
  absorbed by apple).

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
Not executed by the authors yet; any numbers it produces are *new* results and must be reported from
`ai-engine/reports/yolo11_evaluation.json`, never copied from here. The historical CPU baseline (test mAP@0.5 0.410) stays the
reference until then.

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
