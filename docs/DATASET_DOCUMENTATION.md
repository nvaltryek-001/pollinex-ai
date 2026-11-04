# Dataset Documentation

Source of truth: `datasets/dataset_sources.json` (+ `dataset_manifest.csv`). Status values: **integrated**, **script_only**,
**documented_only**, **unverified**, **audited_not_used**, **unreachable**. Verified 2026-11-03.
File-level inventory (every image decoded and hashed): `datasets/reports/dataset_inventory.md`. **1,985 images** (2026-11-04):

| Species | Box-annotated | iNaturalist | Commons | **Total** |
|---|--:|--:|--:|--:|
| apple | 48 | 107 | — | **155** |
| peach | 24 | 71 | — | **95** |
| pear | 18 | 29 | — | **47** |
| sunflower | 628 | 200 | — | **828** |
| hibiscus | — | 91 | 165 | **256** |
| tomato | — | 200 | 147 | **347** |
| strawberry | — | 15 | 29 | **44** |
| brinjal | — | 20 | 111 | **131** |
| chilli | — | 28 | 54 | **82** |

The 628 derived sunflower crops are excluded from these counts. Quality audit (`datasets/reports/dataset_quality_audit.md`, all sources together):
* **Integrity:** 0 corrupt, 0 exact duplicates, 18 images under 160 px.
* **Near-duplicates:** 2 pairs (dHash ≤ 4), checked across all sources and splits.
* **Cross-split leakage:** 1 pair, two photos of the same TF sunflower. The test member is excluded from every test evaluation (`datasets/processed/leakage_exclusions.txt`).
* **Label review:** the one image flagged earlier as suspected label noise was reviewed and kept (`datasets/processed/label_review.csv`). The latest run flags 0.
* **Suitability:** every image supports species recognition. 718 have boxes for detection. 240 sunflower images are close-up structure candidates (largest box ≥ 15 % of the frame); this means a structure *could* be annotated, not that it is visible.

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

## Integrated: iNaturalist flowering photos (image-level species labels)
* Source: iNaturalist API v1, run in GitHub Actions (`.github/workflows/inat.yml`, `download_inat_flowering.py`).
* **Licence, checked per photo:** CC0 140 · CC BY 565 · CC BY-SA 56. iNaturalist's default CC BY-NC licence and ND licences are excluded. Attribution for each file is in `ATTRIBUTION.csv`.
* **Species verification:** taxon resolved by exact name and then re-checked on each observation. Each observation is either Research Grade, or cultivated with ≥ 1 agreeing and 0 disagreeing identifications. It also carries the annotation **Flowers and Fruits = Flowers**, whose term id was verified when the script ran.
* **Kept per species:**

  | Species | Images |
  |---|--:|
  | hibiscus | 91 |
  | tomato | 200 |
  | sunflower | 200 |
  | apple | 107 |
  | peach | 71 |
  | pear | 29 |
  | strawberry | 15 |
  | brinjal | 20 |
  | chilli | 28 |

  One photo per observation, at most 5 per observer.
* **Checks:** decode, minimum side 240 px, SHA-1 and dHash duplicates (all dropped), blur and exposure flags. Splits are 70/15/15 **by observer**; 0 observers appear in more than one split.
* **Labels: species only.** There are no boxes or structures, and these images are never used as detection labels.
* **Limits:**
  * Whole-scene photos; small flowers for tomato and chilli.
  * The flowering annotation is per observation, so a few photos show fruit (seen on `datasets/reports/inat_flowering_<species>.jpg`).
  * **Strawberry, brinjal and chilli have too few openly licensed flowering observations**: most iNaturalist photos are CC BY-NC.

## Integrated: Wikimedia Commons flower categories (image-level species labels)
* Source: Commons API, run in GitHub Actions (`.github/workflows/commons.yml`, `download_commons_flowers.py`).
* **Selection:** only files in sub-categories of `Category:<scientific name>` whose title contains the genus and "flower", "blossom" or "inflorescence". Examples: `Solanum melongena (flowers)`, `Capsicum annuum (flowers)`, `Fragaria × ananassa (flowers)`, and the Hibiscus rosa-sinensis flower close-up categories. Every category used is listed in `datasets/reports/commons_flowers_report.json`.
* **Licence, checked per file:** CC BY-SA 326 · CC0 / public domain 108 · CC BY 72. NC, ND, FAL and GFDL-only files are excluded. Author, licence, licence URL and file page are in `ATTRIBUTION.csv`. 4 CC BY-SA files have no author in their metadata; their attribution is the linked Commons file page.
* **Duplicates and splits:** near-duplicates are removed against all other committed sets (4 dropped, many iNaturalist photos are mirrored on Commons). Splits are by **author**; 0 authors appear in more than one split.
* **Kept per species:**

  | Species | Images |
  |---|--:|
  | hibiscus | 165 |
  | tomato | 147 |
  | brinjal | 111 |
  | chilli | 54 |
  | strawberry | 29 |
* **Label quality:** species labels come from community category curation, which is weaker than iNaturalist Research Grade. I reviewed every contact sheet (`datasets/reports/commons_flowers_<species>.jpg`). Brinjal, chilli and tomato look clean. The strawberry category includes a few non-photo or ground-cover images, which are kept and reported rather than hand-removed.

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
