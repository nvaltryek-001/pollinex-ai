# Annotation statistics

_Generated 2026-11-04T05:17:44.146494+00:00 by `datasets/scripts/annotation_stats.py`._

| Species | Images | Box annotations | Image-level labels |
|---|--:|--:|--:|
| apple | 155 | 2470 | 155 |
| peach | 95 | 924 | 95 |
| pear | 47 | 1257 | 47 |
| sunflower | 828 | 2432 | 828 |
| hibiscus | 256 | 0 | 256 |
| tomato | 347 | 0 | 347 |
| strawberry | 44 | 0 | 44 |
| brinjal | 131 | 0 | 131 |
| chilli | 82 | 0 | 82 |

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

## inat_flowering — image-level species label only (no boxes)

| Species | Images | Boxes | Split | Details |
|---|--:|--:|---|---|
| hibiscus | 91 | 0 | {'train': 71, 'test': 7, 'val': 13} | `{"quality_flags": {}, "label_source": {"research_grade": 19, "cultivated_with_agreement": 72}}` |
| tomato | 200 | 0 | {'train': 138, 'val': 28, 'test': 34} | `{"quality_flags": {}, "label_source": {"research_grade": 180, "cultivated_with_agreement": 20}}` |
| strawberry | 15 | 0 | {'train': 10, 'val': 3, 'test': 2} | `{"quality_flags": {}, "label_source": {"research_grade": 12, "cultivated_with_agreement": 3}}` |
| brinjal | 20 | 0 | {'train': 15, 'val': 4, 'test': 1} | `{"quality_flags": {}, "label_source": {"research_grade": 11, "cultivated_with_agreement": 9}}` |
| chilli | 28 | 0 | {'train': 25, 'test': 1, 'val': 2} | `{"quality_flags": {}, "label_source": {"research_grade": 26, "cultivated_with_agreement": 2}}` |
| sunflower | 200 | 0 | {'train': 142, 'test': 32, 'val': 26} | `{"quality_flags": {"dark": 1}, "label_source": {"research_grade": 182, "cultivated_with_agreement": 18}}` |
| apple | 107 | 0 | {'test': 17, 'train': 67, 'val': 23} | `{"quality_flags": {}, "label_source": {"research_grade": 97, "cultivated_with_agreement": 10}}` |
| peach | 71 | 0 | {'train': 52, 'test': 10, 'val': 9} | `{"quality_flags": {"dark": 1}, "label_source": {"research_grade": 54, "cultivated_with_agreement": 17}}` |
| pear | 29 | 0 | {'test': 5, 'train': 18, 'val': 6} | `{"quality_flags": {}, "label_source": {"research_grade": 21, "cultivated_with_agreement": 8}}` |

## commons_flowers — image-level species label only (no boxes)

| Species | Images | Boxes | Split | Details |
|---|--:|--:|---|---|
| strawberry | 29 | 0 | {'train': 21, 'val': 4, 'test': 4} | `{"quality_flags": {}, "label_source": {"commons:Category:Fragaria \u00d7 ananassa (flowers)": 29}}` |
| brinjal | 111 | 0 | {'train': 94, 'val': 7, 'test': 10} | `{"quality_flags": {"blurry": 4, "dark": 1}, "label_source": {"commons:Category:Solanum melongena (flowers)": 111}}` |
| chilli | 54 | 0 | {'train': 41, 'test': 6, 'val': 7} | `{"quality_flags": {"blurry": 2}, "label_source": {"commons:Category:Capsicum annuum (flowers)": 50, "commons:Category:Capsicum frutescens (flowers)": 4}}` |
| hibiscus | 165 | 0 | {'train': 133, 'val': 16, 'test': 16} | `{"quality_flags": {"blurry": 4}, "label_source": {"commons:Category:Insects on Hibiscus rosa-sinensis flowers": 8, "commons:Category:Hibiscus rosa-sinensis (flowers)": 53, "commons:Category:Close-ups of Hibiscus rosa-sinensis flowers of orange cultivars": 28, "commons:Category:Close-up photographs of Hibiscus rosa-sinensis cultivar flowers": 37, "commons:Category:Close-ups of Hibiscus rosa-sinensis flowers of red cultivars": 39}}` |
| tomato | 147 | 0 | {'train': 92, 'test': 29, 'val': 26} | `{"quality_flags": {"blurry": 3, "dark": 5}, "label_source": {"commons:Category:Solanum lycopersicum (flowers)": 147}}` |

No CVAT exports exist in the repository yet: every structure / centre / stage / health class has 0 annotations. Nothing here is generated or inferred.
