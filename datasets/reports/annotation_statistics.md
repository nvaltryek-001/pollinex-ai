# Annotation statistics

_Generated 2026-11-03T15:28:03.574742+00:00 by `datasets/scripts/annotation_stats.py`._

| Species | Images | Box annotations | Image-level labels |
|---|--:|--:|--:|
| apple | 48 | 2470 | 48 |
| peach | 24 | 924 | 24 |
| pear | 18 | 1257 | 18 |
| sunflower | 628 | 2432 | 628 |
| hibiscus | 0 | 0 | 0 |
| tomato | 0 | 0 | 0 |
| strawberry | 0 | 0 | 0 |
| brinjal | 0 | 0 | 0 |
| chilli | 0 | 0 | 0 |

| Schema class (CVAT) | Annotations |
|---|--:|
| flower_centre | 0 |
| petal | 0 |
| anther | 0 |
| stigma | 0 |
| stamen | 0 |
| pistil | 0 |
| health_issue | 0 |
| flower.stage (any) | 0 |

## usda_fruit_flower — segmentation masks + boxes derived from mask components

| Species | Images | Boxes | Split | Details |
|---|--:|--:|---|---|
| apple | 48 | 2470 | {'train': 29, 'val': 7, 'test': 12} | `{"boxes_per_image": 51.46, "relative_box_area": {"min": 1e-05, "p25": 0.00035, "median": 0.00071, "p75": 0.00161, "max": 0.04679}}` |
| peach | 24 | 924 | {'train': 14, 'val': 4, 'test': 6} | `{"boxes_per_image": 38.5, "relative_box_area": {"min": 1e-05, "p25": 0.00028, "median": 0.0005, "p75": 0.00112, "max": 0.03672}}` |
| pear | 18 | 1257 | {'val': 3, 'test': 4, 'train': 11} | `{"boxes_per_image": 69.83, "relative_box_area": {"min": 1e-05, "p25": 0.00033, "median": 0.0007, "p75": 0.00174, "max": 0.04305}}` |

## tf_flower_detection_sunflower — bounding boxes (YOLO, class flower)

| Species | Images | Boxes | Split | Details |
|---|--:|--:|---|---|
| sunflower | 628 | 2432 | {'train': 439, 'val': 94, 'test': 95} | `{"boxes_per_image": 3.87, "relative_box_area": {"min": 0.0002, "p25": 0.01033, "median": 0.02744, "p75": 0.09783, "max": 0.99956}}` |

No CVAT exports exist in the repository yet: every structure / centre / stage / health class has 0 annotations. Nothing here is generated or inferred.
