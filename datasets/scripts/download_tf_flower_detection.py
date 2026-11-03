#!/usr/bin/env python3
"""Download + verify + inspect the TensorFlow Flower Detection Dataset (Zenodo 7768292, CC BY 4.0).

Not executed in the original build environment (zenodo.org was unreachable there). Run on a machine with
internet access:
    python datasets/scripts/download_tf_flower_detection.py
Then optionally build a YOLO11 run with ai-engine/training/train_yolo11.py --extra-yolo-dir <out>/yolo
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URL = "https://zenodo.org/records/7768292/files/TensorFlowFlowerDetectionDataset.zip?download=1"
MD5 = "bafa11ef76ca62b08b257bd3dc92e0c6"


def md5sum(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "datasets" / "raw" / "tf_flower_detection")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    zpath = args.out / "TensorFlowFlowerDetectionDataset.zip"
    if not zpath.exists():
        print("downloading", URL)
        urllib.request.urlretrieve(URL, zpath)
    got = md5sum(zpath)
    if got != MD5:
        raise SystemExit(f"MD5 mismatch: {got} != {MD5} - refusing to use the archive")
    with zipfile.ZipFile(zpath) as z:
        for m in z.namelist():  # zip-slip guard
            if m.startswith("/") or ".." in Path(m).parts:
                raise SystemExit(f"unsafe path in archive: {m}")
        z.extractall(args.out / "extracted")
    imgs = sorted((args.out / "extracted").rglob("images/*.jpg"))
    lbl_dir = {p.parent.parent for p in imgs}
    classes, n_boxes, missing = Counter(), 0, 0
    pairs = []
    for im in imgs:
        lab = im.parent.parent / "labels" / (im.stem + ".txt")
        if not lab.exists():
            missing += 1
            continue
        rows = [r.split() for r in lab.read_text().splitlines() if r.strip()]
        classes.update(r[0] for r in rows)
        n_boxes += len(rows)
        pairs.append((im, lab))
    # tf_flowers file names are unique per original photo -> split by image (no augmented duplicates in this set)
    random.Random(args.seed).shuffle(pairs)
    n = len(pairs)
    splits = {"train": pairs[: int(0.7 * n)], "val": pairs[int(0.7 * n): int(0.85 * n)], "test": pairs[int(0.85 * n):]}
    yolo = args.out / "yolo"
    for s, items in splits.items():
        for sub in ("images", "labels"):
            (yolo / s / sub).mkdir(parents=True, exist_ok=True)
        for im, lab in items:
            shutil.copy2(im, yolo / s / "images" / im.name)
            shutil.copy2(lab, yolo / s / "labels" / lab.name)
    report = {"dataset_id": "tf_flower_detection", "md5_verified": True, "images": len(imgs),
              "images_without_labels": missing, "boxes": n_boxes, "class_ids": dict(classes),
              "split_sizes": {k: len(v) for k, v in splits.items()}, "label_roots": [str(p) for p in lbl_dir]}
    (ROOT / "datasets" / "reports" / "tf_flower_detection_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
