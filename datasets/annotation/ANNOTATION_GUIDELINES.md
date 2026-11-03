# POLLINEX annotation workflow (CVAT)

Use this when you collect your own images for crops that have no public labelled data
(reproductive structures, flower stages, tomato/brinjal/chilli/hibiscus/sunflower/strawberry boxes).

## 1. Tooling
* CVAT (self-hosted via Docker: `git clone https://github.com/cvat-ai/cvat && docker compose up -d`, or app.cvat.ai).
* Import the label schema `cvat_labels.json` from this folder when creating the project.
* Export as **YOLO 1.1** (boxes) or **COCO 1.0** (polygons) and place the export under
  `datasets/raw/custom_<crop>/`.

## 2. Label schema
| Label | Type | Attributes |
|---|---|---|
| `flower` | box (or polygon) | `species` (select: tomato, brinjal, chilli, apple, pear, peach, strawberry, sunflower, hibiscus, other), `stage` (bud, early_bloom, partially_open, fully_open, senescent), `occluded` (bool), `truncated` (bool) |
| `anther_region` | box / polygon | `pollen_visible` (bool) |
| `stigma` | box / point | `visible_clearly` (bool) |
| `style_class` | tag on `flower` (brinjal only) | long / medium / short |

## 3. Rules (adapted from Schouten et al., 2024)
1. Tight boxes around the visible part of each flower; one box per flower, also when touching.
2. Annotate **every** visible flower above ~10 px; do not skip background flowers (unlabelled flowers become false "false positives").
3. Mark occluded / truncated flowers with the attributes instead of skipping them.
4. Stage is judged from the corolla only; never label pollen viability.
5. Only annotate anthers/stigma that are actually visible at the image resolution.
6. A second person reviews 20 % of images ("4-eyes"); disagreements are resolved and logged in `review_log.csv`.

## 4. Splits and leakage
* Split by **plant / capture session**, never by individual image, so consecutive photos of the same plant stay together.
* Do all augmentation **after** splitting, inside the training loop only.
* Keep a frozen `test` list; do not look at test predictions while tuning.

## 5. Train
```bash
python ai-engine/training/train_yolo11.py --data datasets/raw/custom_tomato/data.yaml --model yolo11n.pt --epochs 100
```
Then copy the exported ONNX file to `ai-engine/models/` (`flower_yolo11n.onnx` for flowers,
`structures_yolo.onnx` for reproductive structures) and reload models from Admin settings.
