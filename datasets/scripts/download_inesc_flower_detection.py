#!/usr/bin/env python3
"""Download + audit the INESC TEC "Flower Detection Dataset" (Zenodo 7708815, CC BY 4.0, YOLO format, 103 originals).

    python datasets/scripts/download_inesc_flower_detection.py

The record does not name the flower species, and its train/val/test folders contain AUGMENTED copies of the 103
originals - a leakage risk. This script only audits: counts, decode check, exact and near-duplicate (dHash) groups
across its splits, class ids, and a crop contact sheet for visual species identification. It does not ingest the data.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
URL = "https://zenodo.org/records/7708815/files/FlowerDetection.zip?download=1"
MD5 = "2ddb4da0bfae7d1e562f79514610d96d"
IMG_EXT = {".jpg", ".jpeg", ".png"}


def dhash(im: Image.Image) -> int:
    g = np.asarray(im.convert("L").resize((9, 8)))
    return int("".join("1" if b else "0" for b in (g[:, 1:] > g[:, :-1]).ravel()), 2)


def main():
    raw = ROOT / "datasets" / "raw" / "inesc_flower_detection"
    raw.mkdir(parents=True, exist_ok=True)
    z = raw / "FlowerDetection.zip"
    if not z.exists():
        urllib.request.urlretrieve(URL, z)
    if hashlib.md5(z.read_bytes()).hexdigest() != MD5:
        raise SystemExit("MD5 mismatch - refusing to use the archive")
    ext = raw / "extracted"
    with zipfile.ZipFile(z) as zf:
        if any(m.startswith("/") or ".." in Path(m).parts for m in zf.namelist()):
            raise SystemExit("unsafe archive")
        zf.extractall(ext)
    imgs = sorted(p for p in ext.rglob("*") if p.suffix.lower() in IMG_EXT)
    split_of = lambda p: next((s for s in ("train", "val", "test") if s in p.parts), "none")  # noqa: E731
    per_split, classes, corrupt = Counter(), Counter(), 0
    hashes, dh = defaultdict(list), {}
    crops = []
    for p in imgs:
        try:
            im = Image.open(p)
            im.load()
        except OSError:
            corrupt += 1
            continue
        per_split[split_of(p)] += 1
        hashes[hashlib.sha1(p.read_bytes()).hexdigest()].append(split_of(p))
        dh[p] = (dhash(im), split_of(p))
        lab = p.parent.parent / "labels" / (p.stem + ".txt")
        if lab.exists():
            for line in lab.read_text().split("\n"):
                v = line.split()
                if len(v) == 5:
                    classes[int(float(v[0]))] += 1
                    if len(crops) < 24:
                        x, y, w, h = map(float, v[1:])
                        W, H = im.size
                        crops.append(ImageOps.fit(im.convert("RGB").crop((int((x - w / 2) * W), int((y - h / 2) * H),
                                                                          int((x + w / 2) * W), int((y + h / 2) * H))), (96, 96)))
    items = list(dh.values())
    cross = sum(1 for i in range(len(items)) for j in range(i + 1, len(items))
                if items[i][1] != items[j][1] and bin(items[i][0] ^ items[j][0]).count("1") <= 6)
    rep = ROOT / "datasets" / "reports"
    sheet = Image.new("RGB", (96 * 8, 96 * 3), "white")
    for k, t in enumerate(crops):
        sheet.paste(t, ((k % 8) * 96, (k // 8) * 96))
    sheet.save(rep / "inesc_flower_detection_crops.jpg", quality=80)
    out = {"dataset_id": "inesc_flower_detection", "source": URL, "license": "CC BY 4.0", "md5_verified": True,
           "image_files": len(imgs), "corrupt": corrupt, "images_per_split": dict(per_split),
           "boxes_per_class_id": dict(classes),
           "exact_duplicate_groups": sum(1 for v in hashes.values() if len(v) > 1),
           "near_duplicate_pairs_across_splits_dhash_le6": cross,
           "decision": "audit only - species not stated by the source and augmented copies cross splits",
           "contact_sheet": "datasets/reports/inesc_flower_detection_crops.jpg"}
    (rep / "inesc_flower_detection_report.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
