# Ethics, licensing and responsible use

## Code and model licences
| Part | Licence | Note |
|---|---|---|
| POLLINEX source code | MIT | `LICENSE` |
| `flower_yolo11n.onnx` | AGPL-3.0 | Trained with Ultralytics YOLO11. Remove it to fall back to the MIT pixel detector (`ai-engine/models/YOLO11_LICENSE_NOTE.md`). |
| `embed_mnv3l.onnx` | BSD-3-Clause | torchvision ImageNet MobileNetV3-Large weights (`embed_mnv3l.json`) |
| Species gallery vectors | Derived from the reference photos | Some references are CC BY-SA photos; the gallery files carry that obligation (share-alike, attribution). |

## Image licences (checked per file, from the manifests)
| Dataset | Licence | Attribution |
|---|---|---|
| USDA Multi-species Fruit Flower | CC BY 4.0 | `datasets/licenses/usda_fruit_flower_CC-BY-4.0.txt` |
| TF Flower Detection (sunflower subset) | CC BY 4.0 (boxes) / CC-BY Flickr (images) | `datasets/processed/tf_flower_detection_sunflower/LICENSE.txt`; 20 of 628 images have no per-image Flickr attribution upstream |
| iNaturalist flowering photos | CC0 140 · CC BY 565 · CC BY-SA 56. NC and ND licences are excluded | `datasets/processed/inat_flowering/ATTRIBUTION.csv` |
| Wikimedia Commons flower photos | CC BY-SA 326 · CC0 / public domain 108 · CC BY 72. NC, ND, FAL and GFDL-only files are excluded | `datasets/processed/commons_flowers/ATTRIBUTION.csv` |

Images are redistributed only under their own licences. Anyone reusing a subset must keep the attribution rows.

## Privacy
* Uploaded images are re-encoded on intake. EXIF metadata, including GPS, is removed (`backend/app/services/storage.py`), and files are stored under content hashes.
* Scans are private to the account that made them. Admins see the activity log, not other users' images.
* Passwords are PBKDF2-hashed. Changing the password or logging out revokes every earlier token.
* iNaturalist and Commons photos are public, community-contributed images. Observer names appear only in the attribution files that the licences require.

## Honest-claims policy (enforced in code and UI)
* Every result carries a method badge: trained model, reference gallery, heuristic, rule-based, close-up fallback or simulation.
* The app never claims pollen viability, stigma receptivity, fertilisation, yield, disease or fruit identification.
* Species that failed the support gate (strawberry) are never returned as an AI answer. They can only be chosen manually.
* Machine box proposals are marked `unverified` and are rejected by the training importer until a person has reviewed them.
* Model choices are made on validation data, and test sets are used once (`*_rule.py` scripts record each decision).

## Intended use and limits
POLLINEX is a decision-support and research tool for growers, students and researchers. It is not an agronomic or
phytosanitary authority. Readiness is a visual estimate, and field checks are still needed before pollinating. The data comes
mostly from temperate regions and community photos, so performance on Indian field conditions, other cultivars, night images
or unusual cameras is unknown until it is measured.
