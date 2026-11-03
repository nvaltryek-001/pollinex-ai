# POLLINEX annotation workflow (CVAT)

**Status (2026-11-03): no structure, stage, centre or health annotations exist yet for any species.** Pollinex never
generates artificial labels for these classes. Everything below is the workflow for creating real ones; the statistics
script (`datasets/scripts/annotation_stats.py`) reports exactly what exists.

## 1. Tooling
* CVAT — self-hosted (`git clone https://github.com/cvat-ai/cvat && cd cvat && docker compose up -d`, open
  http://localhost:8080) or app.cvat.ai.
* Create a project and paste `cvat_labels.json` (this folder) into *Constructor → Raw*.
* One task per **capture session** (one plant / field / day), so splits can follow sessions.
* Export as **COCO 1.0** (keeps polygons, points and attributes) to `datasets/raw/custom_<crop>/annotations.json`,
  images to `datasets/raw/custom_<crop>/images/`.
* Convert + validate: `python datasets/scripts/annotation_stats.py --coco datasets/raw/custom_<crop>/annotations.json --to-yolo`.

## 2. Class definitions
| Label | Shape | Definition | Attributes |
|---|---|---|---|
| `flower` | box | Whole visible flower (corolla incl. visible sepals; sunflower = whole capitulum; strawberry = one flower, not the truss). One box per flower, also when touching. | `species`, `stage`, `occluded`, `truncated`, `style_class` (brinjal) |
| `flower_centre` | point | Geometric centre of the reproductive whorl (where stamens/pistil meet); for sunflower the capitulum centre. One per `flower` whose centre is visible. | — |
| `petal` | polygon | Each visible petal (sunflower: ray florets). Only petals that are ≥ ~50 % visible. | `damage` |
| `anther` | polygon | Pollen-bearing head of a stamen (tomato/brinjal/chilli: the anther cone may be one polygon). | `pollen_visible`, `dehisced` |
| `stigma` | polygon | Receptive tip of the pistil (hibiscus: each of the 5 pads separately). | `receptive_looking` (visual only) |
| `stamen` | polygon | Filament + anther when the filament is visible; otherwise annotate only `anther`. | — |
| `pistil` | polygon | Style + stigma (+ ovary if visible). Hibiscus: the staminal column is **not** the pistil. | — |
| `health_issue` | polygon | A visible abnormality on petals/sepals. Describe, never diagnose a disease. | `kind` |

### Stage definitions (attribute `stage` on `flower`)
| Stage | Visual definition |
|---|---|
| `bud` | Corolla closed; no reproductive organs visible. |
| `early_bloom` | Corolla opening; petals < ~45° from the axis; organs partly visible. |
| `partially_open` | Petals between ~45° and fully spread. |
| `fully_open` | Petals fully spread; anthers/stigma fully exposed. |
| `senescent` | Petals wilting, browning, dropping, or ovary swelling. |
| `uncertain` | Use instead of guessing (counted separately; excluded from training). |

## 3. Rules (adapted from Schouten et al., 2024)
1. Tight boxes around the visible part of each flower.
2. Annotate **every** visible flower above ~10 px; unlabelled flowers become false "false positives".
3. Mark occluded / truncated flowers with attributes instead of skipping them.
4. Stage is judged from the corolla only; never label pollen viability or fertilisation.
5. Annotate anthers/stigma/stamens/pistils **only where they are actually visible** at the image resolution; never infer
   hidden organs from species knowledge.
6. `uncertain` is a valid answer; do not guess species or stage.
7. Two annotators: a second person reviews ≥ 20 % of images; disagreements are logged in `review_log.csv`
   (`image,label,annotator_a,annotator_b,resolution`). `annotation_stats.py --review` reports agreement.

## 4. Splits and leakage
* Split by **capture session / plant**, never by image (`annotation_stats.py --to-yolo` splits by the CVAT task name).
* Augment only after splitting, inside the training loop. Keep a frozen `test` list; tune only on `val`.

## 5. Train
```bash
python ai-engine/training/train_yolo11.py --data datasets/raw/custom_tomato/yolo/data.yaml --imgsz 960
```
Structures: the converter writes a separate YOLO set with classes anther/stigma/stamen/pistil/petal; train it the same
way and export to `ai-engine/models/structures_yolo.onnx`. GPU: `notebooks/train_yolo11_colab.ipynb`.
