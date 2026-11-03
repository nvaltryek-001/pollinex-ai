# Dataset Documentation

Source of truth: `datasets/dataset_sources.json` (+ `dataset_manifest.csv`). Status values: **integrated**, **script_only**,
**documented_only**, **unverified**, **audited_not_used**, **unreachable**. Verified 2026-11-03.
File-level inventory (every image decoded and hashed): `datasets/reports/dataset_inventory.md` — **718 images** (apple 48, peach 24,
pear 18, sunflower 628; tomato, brinjal, chilli, strawberry, hibiscus **0**) + 628 derived sunflower crops. Full audit:
`docs/FINAL_PROJECT_AND_DATASET_AUDIT.md`.

## Integrated: Multi-species Fruit Flower (USDA)
* Citation: Dias, Tabb & Medeiros (2018), *IEEE RA-L* 3(4):3003–3010; data doi:10.15482/USDA.ADC/1423466. Licence CC BY 4.0 (`datasets/licenses/`).
* Obtained from the public GitHub mirror `ai-agriculture-circuits-and-systems/multi-species-fruit-flower` @ `17db8b119a39`.
* 207 original images (apple 165, peach 24, pear 18); **90** have segmentation masks and boxes; 117 have no annotations and are excluded.
* Annotation formats: binary PNG masks; per-image JSON (COCO-like) and CSV boxes.
* Task support: semantic segmentation → instance boxes. **Not** species-level classification beyond the three folders; no stages; no reproductive structures.

### Audit findings
1. **Box orientation:** upstream boxes overlap mask components for 49 % of boxes as-is and 54 % after a vertical flip; the flip
   fits better in 50/90 images — i.e. orientation is inconsistent. Boxes are therefore **not used**; instances are mask components.
2. Touching flowers merge into one mask component → treated as one instance (cluster). This makes counts conservative.
3. Background blossoms are unlabelled → measured precision is pessimistic.
4. Class imbalance: apple 2,470 instances vs peach 924 vs pear 1,257; species ↔ camera setup confound.
5. Quality: 5 images flagged (lowest 5 % Laplacian sharpness): apple_IMG_0266, _0270, _0361, _0392, peach_36 — kept, flagged.

### Splits (leakage control)
Group = capture subset (apple_A, apple_B, peach, pear_seq1, pear_seq2). Within a group images are sorted by frame number and cut
into contiguous 60/15/25 % blocks, so adjacent video frames cannot straddle splits. dHash audit: 0 near-duplicates (Hamming ≤ 6)
across splits; 0 exact duplicates. Result: train 54 (3,070 inst.) · val 14 (652) · test 22 (929). Files:
`datasets/splits/usda_fruit_flower_splits.json`, COCO files in `datasets/annotations/`.
Augmentation is never materialised on disk; the pixel classifier samples pixels per image within the training split only.

## Integrated: TF Flower Detection — sunflower subset
* Boxes: TensorFlow Flower Detection Dataset (INESC TEC, Zenodo 7768292, CC BY 4.0) — 3,554 images, 14,308 boxes, one class "flower".
  Downloaded in GitHub Actions (`.github/workflows/datasets.yml`), MD5 verified, all 3,554 decoded, 2 exact duplicates removed.
* Species: the dataset has no species label. File names were joined with the class folders of TF `flower_photos` (Google, per-image
  CC-BY Flickr licences): daisy 622, dandelion 893, rose 606, sunflower 679, tulip 752. Only **sunflower** is a target crop.
* Committed: `datasets/processed/tf_flower_detection_sunflower/` — 628 images (resized ≤ 1280 px), 2,432 YOLO boxes, splits
  439 / 94 / 95 images (1,665 / 361 / 406 boxes), `data.yaml`, `LICENSE.txt` with attributions (608 of 628 images have a per-image
  line upstream). Gallery crops `datasets/processed/sunflower_gallery/` — references from train+val (533), test crops from test (95).
* Use: species-gallery extension, evaluated on the 95 held-out crops (recall 0.937). Detection: data ready, **no detector trained on it**;
  the deployed USDA detector scores mAP@0.5 0.001 on it.
* Limitation: close-up photos, not field/plantation images.

## Audited, not used
* INESC Flower Detection (Zenodo 7708815, CC BY 4.0): 206 images, 990 boxes; species not stated and not identifiable (grayscale /
  noise-augmented crops); 49 near-duplicate pairs across its splits. `download_inesc_flower_detection.py` reproduces the audit.

## Unreachable / script-only
| Dataset | Licence | Script | Notes |
|---|---|---|---|
| Oxford 102 | terms unverified (research use) | `download_oxford102_subset.py` (sunflower=54, hibiscus=83) | all three mirrors timed out from the build workspace **and** GitHub runners on 2026-11-03; only hibiscus source found |
| FlowerNet (Mendeley) | MIT | `ingest_flowernet_originals.py` | manual download; originals only; dHash dedupe; avoids 5,600 augmented twins |

## Documented only
EWD (CC BY-NC, no target crops), DoPI (GB-only interaction table), FloPE (no public data located), PlantCLEF (terms unverified),
Roboflow/4TU tomato & strawberry sets (licences per project; hosts unreachable).

## Not available
No openly licensed, reachable dataset with **anther / stigma / pollen** annotations or **stage labels** for the nine target crops
was found. `datasets/annotation/ANNOTATION_GUIDELINES.md` + `cvat_labels.json` define the CVAT workflow to create one.

## Rules followed
No invented datasets · no classification labels used for detection · no synthetic images mixed with real ones · independent test
set used once · attribution preserved · no image archives or large weights committed.
