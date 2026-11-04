# Research paper set (50 papers, verified 2026-11-04)

* `POLLINEX_50_PAPERS.csv`: the final list. The same table is in the project's Google Drive folder as a Google Sheet.
* `papers_manifest.{json,csv}`: the raw output of `research/scripts/collect_papers.py`, run through `.github/workflows/papers.yml`. It holds 59 candidates with abstracts.

Every entry comes from OpenAlex (title, authors, year, venue, DOI, citation count, open-access status, licence). Nothing is written from memory.

## Composition
* **30 recent papers (2023–2026):**

  | Topic | Papers |
  |---|--:|
  | Robotic pollination systems | 10 |
  | Flower detection | 6 |
  | Pollination reviews | 2 |
  | Tomato flowers | 2 |
  | Kiwifruit flowers | 2 |
  | Strawberry flowers | 2 |
  | Apple flowers | 2 |
  | Flowering stage | 2 |
  | Chilli/pepper flowers | 1 |
  | Flower datasets | 1 |
* **20 baseline or foundational papers:**
  * YOLO v1/v7/v10/11, Faster R-CNN, Mask R-CNN, RetinaNet, DETR and RT-DETR
  * ResNet, MobileNetV3, ViT, DINOv2 and SAM
  * open-set recognition, MS COCO, Oxford 102
  * Dias 2018 (the USDA dataset), FloPE and Schouten 2024

## Selection
I reviewed all 59 candidates and removed 9 as off-topic or weak:
* date-palm review, nano-drone review, vanilla history review
* tomato gene-regulation paper (SlARF5), rapeseed satellite mapping, crocus dataset
* walnut drone disease study
* low-tier duplicates of the kiwi YOLO11n and chilli-recognition topics (the YOLO-FRNet paper was dropped too)

Papers already in the Drive folder before this run are skipped, matched by title in `ALREADY_IN_DRIVE`.

## PDFs
11 of the 50 have a Creative-Commons open-access PDF that could be downloaded automatically. These are on the
[`research-papers`](https://github.com/nvaltryek-001/pollinex-ai/tree/research-papers) branch, each under its own licence.

The other 39 are not redistributed. For each, the DOI link is in the list:
* subscription papers (Elsevier, IEEE, Springer, Wiley)
* arXiv papers under arXiv's own licence
* open-access papers whose publisher refuses automated download (MDPI, Nature, some PMC copies); these can be opened in a browser
