# Dataset quality audit

_Generated 2026-11-04T13:14:19.854645+00:00 by `datasets/scripts/dataset_quality_audit.py`._

Images checked **1985** · decoded **1985** · corrupt **0** · < 160 px **18** · exact-duplicate groups **0** · near-duplicate pairs **2** · **cross-split leakage pairs 1** · suspected label noise **0** (review list)

| Species | Images | Recognition | Detection (boxes) | Close-up structure candidates | Sources | Splits |
|---|--:|--:|--:|--:|---|---|
| apple | 155 | 155 | 48 | 0 | {'usda_fruit_flower': 48, 'inat_flowering': 107} | {'train': 96, 'val': 30, 'test': 29} |
| brinjal | 131 | 131 | 0 | 0 | {'inat_flowering': 20, 'commons_flowers': 111} | {'train': 109, 'val': 11, 'test': 11} |
| chilli | 82 | 82 | 0 | 0 | {'inat_flowering': 28, 'commons_flowers': 54} | {'train': 66, 'test': 7, 'val': 9} |
| hibiscus | 256 | 256 | 0 | 0 | {'inat_flowering': 91, 'commons_flowers': 165} | {'train': 204, 'test': 23, 'val': 29} |
| peach | 95 | 95 | 24 | 0 | {'usda_fruit_flower': 24, 'inat_flowering': 71} | {'train': 66, 'val': 13, 'test': 16} |
| pear | 47 | 47 | 18 | 0 | {'usda_fruit_flower': 18, 'inat_flowering': 29} | {'val': 9, 'test': 9, 'train': 29} |
| strawberry | 44 | 44 | 0 | 0 | {'inat_flowering': 15, 'commons_flowers': 29} | {'train': 31, 'val': 7, 'test': 6} |
| sunflower | 828 | 828 | 628 | 240 | {'tf_flower_detection_sunflower': 628, 'inat_flowering': 200} | {'train': 581, 'val': 120, 'test': 127} |
| tomato | 347 | 347 | 0 | 0 | {'inat_flowering': 200, 'commons_flowers': 147} | {'train': 230, 'val': 54, 'test': 63} |

## Licences

| Species | Licence counts |
|---|---|
| apple | {'usda_fruit_flower: CC BY 4.0': 48, 'inat_flowering: cc-by': 67, 'inat_flowering: cc0': 34, 'inat_flowering: cc-by-sa': 6} |
| brinjal | {'inat_flowering: cc-by': 17, 'inat_flowering: cc0': 1, 'inat_flowering: cc-by-sa': 2, 'commons_flowers: CC BY-SA 3.0': 37, 'commons_flowers: CC BY-SA 2.5': 1, 'commons_flowers: CC0': 1, 'commons_flowers: Public domain': 6, 'commons_flowers: CC BY 3.0': 8, 'commons_flowers: CC BY-SA 4.0': 46, 'commons_flowers: CC BY 4.0': 2, 'commons_flowers: CC BY 2.5': 1, 'commons_flowers: CC BY-SA 2.0': 5, 'commons_flowers: CC BY 3.0 us': 4} |
| chilli | {'inat_flowering: cc-by': 17, 'inat_flowering: cc0': 10, 'inat_flowering: cc-by-sa': 1, 'commons_flowers: CC BY-SA 2.5': 1, 'commons_flowers: CC BY-SA 3.0': 8, 'commons_flowers: Public domain': 15, 'commons_flowers: CC BY-SA 4.0': 13, 'commons_flowers: CC BY-SA 2.0': 8, 'commons_flowers: CC BY 3.0': 1, 'commons_flowers: CC BY 4.0': 2, 'commons_flowers: CC0': 3, 'commons_flowers: CC BY 3.0 us': 3} |
| hibiscus | {'inat_flowering: cc0': 14, 'inat_flowering: cc-by': 65, 'inat_flowering: cc-by-sa': 12, 'commons_flowers: CC BY 3.0': 13, 'commons_flowers: Public domain': 11, 'commons_flowers: CC0': 39, 'commons_flowers: CC BY-SA 2.5': 1, 'commons_flowers: CC BY-SA 3.0': 23, 'commons_flowers: CC BY 2.0': 8, 'commons_flowers: CC BY-SA 4.0': 46, 'commons_flowers: CC BY-SA 2.0': 6, 'commons_flowers: CC BY 4.0': 13, 'commons_flowers: CC BY 3.0 us': 5} |
| peach | {'usda_fruit_flower: CC BY 4.0': 24, 'inat_flowering: cc-by': 55, 'inat_flowering: cc-by-sa': 6, 'inat_flowering: cc0': 10} |
| pear | {'usda_fruit_flower: CC BY 4.0': 18, 'inat_flowering: cc0': 5, 'inat_flowering: cc-by': 23, 'inat_flowering: cc-by-sa': 1} |
| strawberry | {'inat_flowering: cc0': 5, 'inat_flowering: cc-by': 9, 'inat_flowering: cc-by-sa': 1, 'commons_flowers: CC BY-SA 3.0': 12, 'commons_flowers: CC BY-SA 2.5': 1, 'commons_flowers: Public domain': 3, 'commons_flowers: CC BY-SA 4.0': 7, 'commons_flowers: CC0': 3, 'commons_flowers: CC BY 4.0': 2, 'commons_flowers: CC BY-SA 2.0': 1} |
| sunflower | {'tf_flower_detection_sunflower: CC BY 4.0 (boxes) / CC-BY Flickr (image)': 628, 'inat_flowering: cc-by': 158, 'inat_flowering: cc0': 35, 'inat_flowering: cc-by-sa': 7} |
| tomato | {'inat_flowering: cc-by-sa': 20, 'inat_flowering: cc-by': 154, 'inat_flowering: cc0': 26, 'commons_flowers: CC BY-SA 3.0': 49, 'commons_flowers: Public domain': 7, 'commons_flowers: CC0': 20, 'commons_flowers: CC BY-SA 4.0': 49, 'commons_flowers: CC BY 4.0': 1, 'commons_flowers: CC BY-SA 2.5': 2, 'commons_flowers: CC BY-SA 3.0 de': 1, 'commons_flowers: CC BY-SA 2.0': 8, 'commons_flowers: CC BY 2.0': 6, 'commons_flowers: CC BY-SA 2.0 de': 1, 'commons_flowers: CC BY 3.0': 1, 'commons_flowers: CC BY 3.0 us': 2} |

## Cross-split leakage pairs

- `datasets/processed/tf_flower_detection_sunflower/val/images/2588453601_66f2a03cca_n.jpg` (val) ~ `datasets/processed/tf_flower_detection_sunflower/test/images/2588234269_c4bfd0d8b9_n.jpg` (test), Hamming 3 - resolved: test member excluded from evaluation (datasets/processed/leakage_exclusions.txt)

closeup_structure_candidate = boxes exist AND largest box >= 15 % of the image AND >= 160 px min side; it says a flower is large enough to annotate structures, not that they are visible
