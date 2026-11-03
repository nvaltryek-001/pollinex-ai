# Dataset inventory (actual files)

_Generated 2026-11-03T16:12:20.985915+00:00 by `datasets/scripts/audit_datasets.py`._

**Dataset images present: 1479** (masks and report figures excluded).

| Species | Images present |
|---|---|
| hibiscus | 91 |
| tomato | 200 |
| sunflower | 828 |
| apple | 155 |
| peach | 95 |
| pear | 47 |
| strawberry | 15 |
| brinjal | 20 |
| chilli | 28 |
| unspecified | 0 |

| Location | Images | Masks | Derived crops | Decoded OK | Corrupt | MB | Formats |
|---|---|---|---|---|---|---|---|
| `processed/inat_flowering` | 761 | 0 | 0 | 761 | 0 | 104.0 | {'.jpg': 761} |
| `processed/sunflower_gallery` | 0 | 0 | 628 | 628 | 0 | 9.4 | {'.jpg': 628} |
| `processed/tf_flower_detection_sunflower` | 628 | 0 | 0 | 628 | 0 | 26.7 | {'.jpg': 628} |
| `processed/usda_fruit_flower` | 90 | 90 | 0 | 180 | 0 | 51.7 | {'.jpg': 90, '.png': 90} |
| `reports` | 0 | 0 | 0 | 11 | 0 | 1.6 | {'.jpg': 11} |

Exact duplicate groups: **0**

YOLO image/label pairing:

- `processed/usda_fruit_flower/images`: {'images': 90, 'label_files': 90, 'images_without_labels': 0, 'labels_without_images': 0}
- `processed/tf_flower_detection_sunflower/test/images`: {'images': 95, 'label_files': 95, 'images_without_labels': 0, 'labels_without_images': 0}
- `processed/tf_flower_detection_sunflower/train/images`: {'images': 439, 'label_files': 439, 'images_without_labels': 0, 'labels_without_images': 0}
- `processed/tf_flower_detection_sunflower/val/images`: {'images': 94, 'label_files': 94, 'images_without_labels': 0, 'labels_without_images': 0}

Empty directories: ['raw']
