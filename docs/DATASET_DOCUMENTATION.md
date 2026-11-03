# Dataset Documentation

Source of truth: `datasets/dataset_sources.json` (+ `dataset_manifest.csv`). Status values: **integrated**, **script_only**,
**documented_only**, **unverified**. Verified 2026-11-02.

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

## Script-only (hosts unreachable from the build environment)
| Dataset | Licence | Script | Notes |
|---|---|---|---|
| TensorFlow Flower Detection (Zenodo 7768292) | CC BY 4.0 | `download_tf_flower_detection.py` | MD5-verified download, zip-slip guard, class & box stats, 70/15/15 split |
| Oxford 102 | terms unverified (research use) | `download_oxford102_subset.py --map sunflower=<id> hibiscus=<id>` | classification only → gallery; official `setid.mat` split; contact sheet to **verify label ids** |
| FlowerNet (Mendeley) | MIT | `ingest_flowernet_originals.py` | originals only; dHash dedupe; avoids 5,600 augmented twins |

## Documented only
EWD (CC BY-NC, no target crops), DoPI (GB-only interaction table), FloPE (no public data located), PlantCLEF (terms unverified),
Roboflow/4TU tomato & strawberry sets (licences per project; hosts unreachable).

## Not available
No openly licensed, reachable dataset with **anther / stigma / pollen** annotations or **stage labels** for the nine target crops
was found. `datasets/annotation/ANNOTATION_GUIDELINES.md` + `cvat_labels.json` define the CVAT workflow to create one.

## Rules followed
No invented datasets · no classification labels used for detection · no synthetic images mixed with real ones · independent test
set used once · attribution preserved · no image archives or large weights committed.
