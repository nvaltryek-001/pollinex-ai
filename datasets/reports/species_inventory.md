# Species dataset inventory

Generated 2026-11-04T13:15:01+00:00 by `datasets/scripts/build_species_inventory.py` from the files on disk.

Totals: 1985 images, 1985 decode, [] corrupt, 0 exact-duplicate groups, 2 near-duplicate pairs, [{'a': 'datasets/processed/tf_flower_detection_sunflower/val/images/2588453601_66f2a03cca_n.jpg', 'a_split': 'val', 'b': 'datasets/processed/tf_flower_detection_sunflower/test/images/2588234269_c4bfd0d8b9_n.jpg', 'b_split': 'test', 'hamming': 3, 'same_species': True, 'resolved_by_test_exclusion': True}] cross-split leakage pair (excluded from test: 2588234269_c4bfd0d8b9_n).

| Species | Images | train / val / test | Classification labels | Images with boxes | Boxes | Sources |
|---|--:|---|--:|--:|--:|---|
| apple | 155 | 96 / 30 / 29 | 155 | 48 | 2470 | usda_fruit_flower 48, inat_flowering 107 |
| peach | 95 | 66 / 13 / 16 | 95 | 24 | 924 | usda_fruit_flower 24, inat_flowering 71 |
| pear | 47 | 29 / 9 / 9 | 47 | 18 | 1257 | usda_fruit_flower 18, inat_flowering 29 |
| sunflower | 828 | 581 / 120 / 127 | 828 | 628 | 2432 | tf_flower_detection_sunflower 628, inat_flowering 200 |
| hibiscus | 256 | 204 / 29 / 23 | 256 | 0 | 0 | inat_flowering 91, commons_flowers 165 |
| tomato | 347 | 230 / 54 / 63 | 347 | 0 | 0 | inat_flowering 200, commons_flowers 147 |
| strawberry | 44 | 31 / 7 / 6 | 44 | 0 | 0 | inat_flowering 15, commons_flowers 29 |
| brinjal | 131 | 109 / 11 / 11 | 131 | 0 | 0 | inat_flowering 20, commons_flowers 111 |
| chilli | 82 | 66 / 9 / 7 | 82 | 0 | 0 | inat_flowering 28, commons_flowers 54 |

Only USDA and TF Flower Detection images carry boxes. iNaturalist and Commons photos are image-level species labels and are never used as detection data.

## External datasets

| Dataset | Status | Note |
|---|---|---|
| Multi-species Fruit Flower Detection (apple, peach, pear) | integrated | Processed set (90 images + masks + YOLO labels) committed in datasets/processed/usda_fruit_flower; original 207-image archive (~6 GB clone) is re-created by the |
| TensorFlow Flower Detection Dataset (INESC TEC) | integrated | Only the sunflower subset (628 images, 2,432 boxes) is committed; other classes are not target crops. Close-up photos, not field crops. |
| iNaturalist flowering photos (species-verified, openly licensed) | integrated |  |
| Wikimedia Commons flower categories (strawberry, brinjal, chilli, hibiscus, tomato) | integrated |  |
| TensorFlow flower_photos (5 classes, Google) | integrated | Not committed as a separate dataset; per-image attributions for the committed sunflower subset are in its LICENSE.txt |
| Flower Detection Dataset (INESC TEC) | audited_not_used | species unknown; 49 near-duplicate pairs cross its train/val/test splits (augmented copies) - leakage risk |
| Oxford 102 Category Flower Dataset | unreachable | robots.ox.ac.uk and thor.robots.ox.ac.uk mirrors timed out from the build workspace and from GitHub Actions runners (2026-11-03). Script ready; run it on a mach |
| FlowerNet: A Multi-Class Flower Image Dataset | script_only |  |
| Eindhoven Wildflower Dataset (EWD) | documented_only | Non-commercial licence and none of the nine target crops; useful for methodology (tiling, annotation rules), not ingested. |
| DoPI - Database of Pollinator Interactions | documented_only | Great Britain only; not representative of Indian field conditions for the target crops. Importer planned for knowledge-base enrichment with explicit geographic  |
| FloPE synthetic pose data | documented_only | No public dataset download located for this project; method informs our image-space pose module only. |
| PlantCLEF (LifeCLEF) | unverified | Could not verify current terms; very large; not needed for nine crops. |
| Anther / stigma / pollen annotated images for the 9 target crops | documented_only | No openly licensed, reachable dataset with anther/stigma annotations for these crops was found. A CVAT annotation workflow is provided (datasets/annotation/). |
| Tomato / strawberry flower detection sets on Roboflow Universe, 4TU (Rob2Pheno) and Hugging Face | unverified | Hosts unreachable from the build environment; licences not verified. Candidates for future ingestion via the generic YOLO ingest script. |
