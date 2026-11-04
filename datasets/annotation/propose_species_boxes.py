#!/usr/bin/env python3
"""Machine box PROPOSALS for species-labelled photos that have no boxes. These are never ground truth.

    python datasets/annotation/propose_species_boxes.py [--species hibiscus tomato ...] [--conf 0.15]

For every iNaturalist / Wikimedia Commons photo (all splits; the split is kept so reviewed labels stay leakage-free) the
deployed YOLO11 flower detector proposes `flower` boxes. Each proposal carries the photo's species label (from the
source) and `"verified": false`. Output, per species:
    datasets/annotation/proposals/<species>_proposals_coco.json   (COCO; import into CVAT as pre-annotations)
    datasets/annotation/proposals/proposals_manifest.csv          (file, species, split, source, n_proposals, licence)
A human must correct every image in CVAT; import_verified_boxes.py only accepts reviewed exports. The detector was
trained on apple/peach/pear/sunflower boxes only, so proposals for other species are expected to be incomplete.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-engine"))
from pollinex_ai.detector import load_default_detector  # noqa: E402

PROC = ROOT / "datasets" / "processed"
OUT = ROOT / "datasets" / "annotation" / "proposals"
SOURCES = ("inat_flowering", "commons_flowers")
ALL = ["apple", "peach", "pear", "sunflower", "hibiscus", "tomato", "strawberry", "brinjal", "chilli"]


def photos(species: set[str]) -> list[dict]:
    rows = []
    for src in SOURCES:
        man = PROC / src / "manifest.csv"
        for r in csv.DictReader(man.open(encoding="utf-8")):
            if r["species"] in species:
                rows.append({"source": src, "species": r["species"], "split": r["split"], "file": r["file"],
                             "path": PROC / src / r["file"], "licence": r["licence"]})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--species", nargs="+", default=ALL)
    ap.add_argument("--conf", type=float, default=0.15, help="proposal confidence floor (low on purpose: humans delete)")
    args = ap.parse_args()
    det = load_default_detector()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest, summary = [], {}
    for sp in args.species:
        items = photos({sp})
        coco = {"info": {"description": f"POLLINEX machine box proposals for {sp} - UNVERIFIED, not ground truth",
                         "detector": f"{det.backend} {det.version}", "conf_floor": args.conf,
                         "date_created": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                "licenses": [], "categories": [{"id": 1, "name": "flower", "supercategory": "plant"}], "images": [], "annotations": []}
        n_boxes, empty = 0, 0
        for i, it in enumerate(items, start=1):
            if not it["path"].exists():
                continue
            rgb = np.array(Image.open(it["path"]).convert("RGB"))
            H, W = rgb.shape[:2]
            dets = det.detect(rgb, conf_threshold=args.conf).detections
            coco["images"].append({"id": i, "file_name": f"{it['source']}/{it['file']}", "width": W, "height": H,
                                   "split": it["split"], "species": sp, "licence": it["licence"]})
            for d in dets:
                x1, y1, x2, y2 = d.box
                coco["annotations"].append({"id": len(coco["annotations"]) + 1, "image_id": i, "category_id": 1,
                                            "bbox": [round(x1, 1), round(y1, 1), round(x2 - x1, 1), round(y2 - y1, 1)],
                                            "area": round((x2 - x1) * (y2 - y1), 1), "iscrowd": 0, "score": round(d.score, 3),
                                            "attributes": {"species": sp, "verified": False, "source": "machine_proposal"}})
            n_boxes += len(dets)
            empty += not dets
            manifest.append({"file": f"{it['source']}/{it['file']}", "species": sp, "split": it["split"], "source": it["source"],
                             "n_proposals": len(dets), "licence": it["licence"], "status": "unverified_proposal"})
        (OUT / f"{sp}_proposals_coco.json").write_text(json.dumps(coco))
        summary[sp] = {"photos": len(coco["images"]), "proposed_boxes": n_boxes, "photos_without_proposal": empty,
                       "splits": dict(Counter(im["split"] for im in coco["images"]))}
        print(sp, summary[sp], flush=True)
    with (OUT / "proposals_manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(manifest[0].keys()))
        w.writeheader()
        w.writerows(manifest)
    (OUT / "proposals_summary.json").write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                            "status": "UNVERIFIED machine proposals - not ground truth",
                                                            "detector": f"{det.backend} {det.version}", "conf_floor": args.conf,
                                                            "per_species": summary}, indent=2))


if __name__ == "__main__":
    main()
