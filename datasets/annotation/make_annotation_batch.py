#!/usr/bin/env python3
"""Build a CVAT annotation batch for reproductive structures (anther, stigma, stamen, pistil, petal) from committed images.

    python datasets/annotation/make_annotation_batch.py --per-species 40 [--out datasets/raw/annotation_batch]

Selection (no labels are created here - this only chooses WHICH real images humans should annotate first):
  * box-annotated close-ups first: images whose largest flower box covers >= 15 % of the frame (dataset_quality_audit.py
    'closeup_structure_candidate'), then image-level close-up photos (iNaturalist / Wikimedia Commons) of every species,
    preferring larger images and excluding anything in a TEST split (structure test sets are built from new sessions).
  * one CVAT task per (species, source) so the COCO export can be split by session with annotation_stats.py --to-yolo.
Writes <out>/<task>/*.jpg (copies), <out>/tasks.csv (task, file, species, source, original path, licence, attribution),
and <out>/README.txt with the CVAT import steps. Licences/attribution travel with every file.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "datasets" / "processed"
AUDIT = ROOT / "datasets" / "reports" / "dataset_quality_audit.json"


def boxed_closeups() -> list[dict]:
    out = []
    root = PROC / "tf_flower_detection_sunflower"
    for split in ("train", "val"):
        for im in sorted((root / split / "images").glob("*.jpg")):
            rows = [list(map(float, ln.split()[1:])) for ln in (root / split / "labels" / f"{im.stem}.txt").read_text().splitlines() if ln.strip()]
            W, H = Image.open(im).size
            big = max((w * h for _, _, w, h in rows), default=0)
            side = max((min(w * W, h * H) for _, _, w, h in rows), default=0)
            if big >= 0.15 and side >= 160:
                out.append({"path": im, "species": "sunflower", "source": "tf_flower_detection_sunflower", "score": big,
                            "licence": "CC BY 4.0 boxes / CC-BY Flickr image (see LICENSE.txt)", "attribution": "see LICENSE.txt"})
    return out


def image_level() -> list[dict]:
    out = []
    for name in ("inat_flowering", "commons_flowers"):
        man = PROC / name / "manifest.csv"
        if not man.exists():
            continue
        attrib = {}
        att = PROC / name / "ATTRIBUTION.csv"
        if att.exists():
            for r in csv.DictReader(att.open(encoding="utf-8")):
                attrib[r["file"]] = r.get("attribution") or r.get("author", "")
        for r in csv.DictReader(man.open(encoding="utf-8")):
            if r["split"] == "test":
                continue
            p = PROC / name / r["file"]
            out.append({"path": p, "species": r["species"], "source": name, "score": int(r["width"]) * int(r["height"]),
                        "licence": r["licence"], "attribution": attrib.get(r["file"], "")})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-species", type=int, default=40)
    ap.add_argument("--out", type=Path, default=ROOT / "datasets" / "raw" / "annotation_batch")
    args = ap.parse_args()
    pool = boxed_closeups() + image_level()
    chosen = []
    for sp in sorted({p["species"] for p in pool}):
        cands = sorted([p for p in pool if p["species"] == sp], key=lambda p: (p["source"] != "tf_flower_detection_sunflower", -p["score"]))
        chosen += cands[:args.per_species]
    if args.out.exists():
        shutil.rmtree(args.out)
    rows = []
    for c in chosen:
        task = f"{c['species']}__{c['source']}"
        dest = args.out / task / c["path"].name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(c["path"], dest)
        rows.append({"task": task, "file": f"{task}/{c['path'].name}", "species": c["species"], "source": c["source"],
                     "original": str(c["path"].relative_to(ROOT)), "licence": c["licence"], "attribution": c["attribution"]})
    with open(args.out / "tasks.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["task"])
        w.writeheader()
        w.writerows(rows)
    (args.out / "README.txt").write_text(
        "CVAT: create a project with datasets/annotation/cvat_labels.json, then one task per folder here.\n"
        "Annotate ONLY structures that are actually visible (ANNOTATION_GUIDELINES.md). Export COCO 1.0 to\n"
        "datasets/raw/custom_structures/annotations.json (images under datasets/raw/custom_structures/images/<task>/), then\n"
        "  python datasets/scripts/annotation_stats.py --coco datasets/raw/custom_structures/annotations.json --to-yolo\n"
        "  python ai-engine/training/train_yolo11.py --data datasets/raw/custom_structures/yolo_structures/data.yaml --imgsz 960\n"
        "and copy the exported ONNX to ai-engine/models/structures_yolo.onnx (+ .json with names) - the app then reports\n"
        "trained structure detections instead of the heuristic. Licence + attribution per file: tasks.csv.\n", encoding="utf-8")
    summary = {sp: sum(r["species"] == sp for r in rows) for sp in sorted({r["species"] for r in rows})}
    print(json.dumps({"images": len(rows), "per_species": summary, "out": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
