# usda_fruit_flower preparation report

- Upstream: https://github.com/ai-agriculture-circuits-and-systems/multi-species-fruit-flower @ `17db8b119a39`
- Licence: CC BY 4.0 · DOI 10.15482/USDA.ADC/1423466
- Images kept: **90**  · boxes: **4651**
- Excluded: {'degenerate_upstream_box': 246, 'no_box_annotations': 117}

| Split | Images | Boxes | Species mix |
|---|---|---|---|
| train | 54 | 3070 | {'apple': 29, 'peach': 14, 'pear': 11} |
| val | 14 | 652 | {'apple': 7, 'peach': 4, 'pear': 3} |
| test | 22 | 929 | {'apple': 12, 'peach': 6, 'pear': 4} |

| Species | Images | Boxes |
|---|---|---|
| apple | 48 | 2470 |
| peach | 24 | 924 |
| pear | 18 | 1257 |

- Capture groups: {'apple_B': 18, 'apple_A': 30, 'peach': 24, 'pear_seq1': 11, 'pear_seq2': 7}
- Relative box area p5/median/p95: {'p5': 9.17686318131257e-05, 'median': 0.0006507230255839822, 'p95': 0.005541605246066388}
- Exact duplicates: 0 · near-duplicate pairs across splits (dHash<=6): 0
- Low-quality flags (blur p5 or extreme brightness): ['apple_IMG_0266', 'apple_IMG_0270', 'apple_IMG_0361', 'apple_IMG_0392', 'peach_36']

## Ground-truth policy and upstream box audit

- instances = 8-connected components of upstream masks with area >= 9px; touching flowers form one instance (cluster).
- Upstream boxes: 4631; mean fraction overlapping a mask component as-is = 0.49, after vertical flip = 0.54; flip matches better in 50/90 images.
- Conclusion: upstream JSON/CSV boxes are inconsistently oriented (often vertically flipped) relative to images and masks; they are excluded from training and evaluation.
- Note: annotators labelled the foreground tree only; distant background blossoms are unlabelled, which penalises detectors that find them (counted as false positives).

**Class imbalance:** apple contributes most boxes; peach and pear each come from a single camera setup, so species is confounded with capture conditions. Species results on this data must not be read as field-general species recognition.
