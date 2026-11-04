# Deployed model evaluation results

Generated 2026-11-04T11:21:24+00:00 by `python scripts/evaluate_deployed_models.py` on the repository datasets. Nothing was trained or tuned by this script; the shipped artifacts were loaded and run on held-out **test** splits.

Detection and species classification are different tasks and are reported separately. Neither number says anything about fruit, disease, pollen viability or fertilisation, which no model in this project predicts.

## 1. Dataset integrity

Overall: **passed**.

| Dataset | Images | Boxes | Invalid label rows | Cross-split exact duplicates |
|---|--:|--:|--:|--:|
| usda_fruit_flower | 90 | 4651 | 0 | 0 |
| tf_flower_detection_sunflower | 627 | 2431 | 0 | 0 |
| inat_flowering | 761 | - | - | 0 |
| commons_flowers | 506 | - | - | 0 |

Test images excluded for near-duplicate leakage: 2588234269_c4bfd0d8b9_n.

## 2. Flower detection - yolo11-onnx flower_yolo11n

IoU 0.5 for precision/recall/mAP@0.5; mAP@0.5:0.95 averages IoU 0.50-0.95. Confidence floor 0.05 for the PR curve.

| Test set | Species | Images | Boxes | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---|--:|--:|--:|--:|--:|--:|
| usda_fruit_flower | **all** | 22 | 929 | 0.313 | 0.778 | 0.593 | 0.332 |
| | apple | 12 | 503 | 0.332 | 0.801 | 0.602 | 0.331 |
| | peach | 6 | 170 | 0.269 | 0.765 | 0.568 | 0.278 |
| | pear | 4 | 256 | 0.311 | 0.742 | 0.609 | 0.379 |
| tf_flower_detection_sunflower | **all** | 94 | 405 | 0.628 | 0.921 | 0.871 | 0.694 |

Precision/recall above are at the 0.05 confidence floor (all candidate boxes). At the deployed threshold:

- usda_fruit_flower: threshold 0.30 -> precision 0.647, recall 0.578
- tf_flower_detection_sunflower: threshold 0.30 -> precision 0.817, recall 0.837

No box annotations exist for hibiscus, tomato, strawberry, brinjal or chilli, so **no detection performance is claimed for those species**.

## 3. Species classification - reference gallery

Gallery `mnv3l-v1`, k=7, threshold 0.3. 1182 held-out test items.

**Accuracy 0.874 · macro-F1 0.862**

| Species | Precision | Recall | F1 | Test support |
|---|--:|--:|--:|--:|
| apple | 0.851 | 0.933 | 0.890 | 403 |
| brinjal | 0.667 | 0.909 | 0.769 | 11 |
| chilli | 1.000 | 0.714 | 0.833 | 7 |
| hibiscus | 0.778 | 0.913 | 0.840 | 23 |
| peach | 0.848 | 0.918 | 0.881 | 158 |
| pear | 0.855 | 0.855 | 0.855 | 165 |
| sunflower | 0.952 | 0.937 | 0.944 | 126 |
| tomato | 0.925 | 0.984 | 0.954 | 63 |
| unknown | 0.934 | 0.686 | 0.791 | 226 |

Confusion matrix (rows = true, columns = predicted):

| true \ pred | apple | brinjal | chilli | hibiscus | peach | pear | sunflower | tomato | unknown |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| apple | 376 | 0 | 0 | 1 | 8 | 9 | 0 | 0 | 9 |
| brinjal | 0 | 10 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| chilli | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| hibiscus | 0 | 0 | 0 | 21 | 0 | 0 | 1 | 1 | 0 |
| peach | 1 | 0 | 0 | 2 | 145 | 7 | 3 | 0 | 0 |
| pear | 19 | 0 | 0 | 0 | 4 | 141 | 0 | 0 | 1 |
| sunflower | 1 | 0 | 0 | 2 | 1 | 0 | 118 | 3 | 1 |
| tomato | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 62 | 0 |
| unknown | 45 | 3 | 0 | 0 | 13 | 8 | 1 | 1 | 155 |

By test source:

| Source | Items | Accuracy | Macro-F1 |
|---|--:|--:|--:|
| usda_test_flowers | 694 | 0.924 | 0.923 |
| usda_test_background | 220 | 0.705 | 0.827 |
| sunflower_closeup_test | 94 | 0.979 | 0.989 |
| inat_test | 109 | 0.798 | 0.591 |
| commons_test | 65 | 0.892 | 0.707 |

Species not enabled in the gallery (strawberry) are scored as correct only when predicted 'unknown'. 'usda_test_background' items are non-flower crops whose correct answer is 'unknown'.
