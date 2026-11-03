# datasets/

| Path | Content | Committed? |
|---|---|---|
| `dataset_sources.json` | verified source, licence, task support, status, issues for every dataset investigated | yes |
| `dataset_manifest.csv` | flat manifest generated from the JSON | yes |
| `licenses/` | licence texts of integrated datasets | yes |
| `scripts/` | prepare / download / ingest scripts | yes |
| `annotation/` | CVAT label schema and annotation guidelines | yes |
| `splits/` | split membership (image ids) | yes |
| `annotations/` | COCO json derived from masks (small) | yes |
| `reports/` | preparation and audit reports | yes |
| `raw/`, `processed/` | downloaded / converted images | **no** (git-ignored; rebuild with scripts) |

```bash
# integrate the training data (clones ~6 GB if --src is not given)
python datasets/scripts/prepare_usda_fruit_flower.py --src /path/to/multi-species-fruit-flower
# optional extra sources (need internet)
python datasets/scripts/download_tf_flower_detection.py
python datasets/scripts/download_oxford102_subset.py --map sunflower=<label> hibiscus=<label>
python datasets/scripts/ingest_flowernet_originals.py --src <extracted FlowerNet> --species hibiscus
```
See `docs/DATASET_DOCUMENTATION.md` for licences, audits and leakage rules.
