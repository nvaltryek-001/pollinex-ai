# Dataset quality audit

_Generated 2026-11-04T03:31:45.023662+00:00 by `datasets/scripts/dataset_quality_audit.py`._

Images checked **1479** · decoded **1479** · corrupt **0** · < 160 px **18** · exact-duplicate groups **0** · near-duplicate pairs **2** · **cross-split leakage pairs 1** · suspected label noise **1** (review list)

| Species | Images | Recognition | Detection (boxes) | Close-up structure candidates | Sources | Splits |
|---|--:|--:|--:|--:|---|---|
| apple | 155 | 155 | 48 | 0 | {'usda_fruit_flower': 48, 'inat_flowering': 107} | {'train': 96, 'val': 30, 'test': 29} |
| brinjal | 20 | 20 | 0 | 0 | {'inat_flowering': 20} | {'train': 15, 'val': 4, 'test': 1} |
| chilli | 28 | 28 | 0 | 0 | {'inat_flowering': 28} | {'train': 25, 'test': 1, 'val': 2} |
| hibiscus | 91 | 91 | 0 | 0 | {'inat_flowering': 91} | {'train': 71, 'test': 7, 'val': 13} |
| peach | 95 | 95 | 24 | 0 | {'usda_fruit_flower': 24, 'inat_flowering': 71} | {'train': 66, 'val': 13, 'test': 16} |
| pear | 47 | 47 | 18 | 0 | {'usda_fruit_flower': 18, 'inat_flowering': 29} | {'val': 9, 'test': 9, 'train': 29} |
| strawberry | 15 | 15 | 0 | 0 | {'inat_flowering': 15} | {'train': 10, 'val': 3, 'test': 2} |
| sunflower | 828 | 828 | 628 | 240 | {'tf_flower_detection_sunflower': 628, 'inat_flowering': 200} | {'train': 581, 'val': 120, 'test': 127} |
| tomato | 200 | 200 | 0 | 0 | {'inat_flowering': 200} | {'train': 138, 'val': 28, 'test': 34} |

## Licences

| Species | Licence counts |
|---|---|
| apple | {'usda_fruit_flower: CC BY 4.0': 48, 'inat_flowering: cc-by': 67, 'inat_flowering: cc0': 34, 'inat_flowering: cc-by-sa': 6} |
| brinjal | {'inat_flowering: cc-by': 17, 'inat_flowering: cc0': 1, 'inat_flowering: cc-by-sa': 2} |
| chilli | {'inat_flowering: cc-by': 17, 'inat_flowering: cc0': 10, 'inat_flowering: cc-by-sa': 1} |
| hibiscus | {'inat_flowering: cc0': 14, 'inat_flowering: cc-by': 65, 'inat_flowering: cc-by-sa': 12} |
| peach | {'usda_fruit_flower: CC BY 4.0': 24, 'inat_flowering: cc-by': 55, 'inat_flowering: cc-by-sa': 6, 'inat_flowering: cc0': 10} |
| pear | {'usda_fruit_flower: CC BY 4.0': 18, 'inat_flowering: cc0': 5, 'inat_flowering: cc-by': 23, 'inat_flowering: cc-by-sa': 1} |
| strawberry | {'inat_flowering: cc0': 5, 'inat_flowering: cc-by': 9, 'inat_flowering: cc-by-sa': 1} |
| sunflower | {'tf_flower_detection_sunflower: CC BY 4.0 (boxes) / CC-BY Flickr (image)': 628, 'inat_flowering: cc-by': 158, 'inat_flowering: cc0': 35, 'inat_flowering: cc-by-sa': 7} |
| tomato | {'inat_flowering: cc-by-sa': 20, 'inat_flowering: cc-by': 154, 'inat_flowering: cc0': 26} |

## Cross-split leakage pairs

- `datasets/processed/tf_flower_detection_sunflower/val/images/2588453601_66f2a03cca_n.jpg` (val) ~ `datasets/processed/tf_flower_detection_sunflower/test/images/2588234269_c4bfd0d8b9_n.jpg` (test), Hamming 3

## Suspected label noise (for human review; labels NOT changed)

- `datasets/processed/inat_flowering/test/strawberry/inat_6122153_7664616.jpg`: labelled strawberry, 5 nearest neighbours are apple (cos >= 0.815)

closeup_structure_candidate = boxes exist AND largest box >= 15 % of the image AND >= 160 px min side; it says a flower is large enough to annotate structures, not that they are visible
