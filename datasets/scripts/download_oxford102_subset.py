#!/usr/bin/env python3
"""Build species *reference-gallery* folders (classification only) from Oxford 102 Flowers.

    python datasets/scripts/download_oxford102_subset.py                      # sunflower=54, hibiscus=83 (1-based)
    python ai-engine/training/extend_gallery.py --extra datasets/processed/oxford102_gallery

* Oxford-102 has image-level labels only: it may extend the open-set species gallery but must NEVER be used as
  detector training data (no boxes).
* Class indices follow the published 102-class name list (1-based in imagelabels.mat). A low-resolution contact sheet
  per species is written to datasets/reports/ so the mapping is verified by looking at it.
* The official setid.mat split is kept: trnid+valid -> gallery/, tstid -> test/ (never added to the gallery).
* Licence/terms of the images are not stated on the dataset page; images are NOT committed to the repository
  (only this script, the manifest and the small verification sheets are).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://www.robots.ox.ac.uk/~vgg/data/flowers/102/"
DEFAULT_MAP = ["sunflower=54", "hibiscus=83"]


def fetch(name: str, dest: Path) -> Path:
    p = dest / name
    if not p.exists():
        print("downloading", BASE + name)
        urllib.request.urlretrieve(BASE + name, p)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", nargs="+", default=DEFAULT_MAP, help="species_id=oxford_label (1-based)")
    ap.add_argument("--raw", type=Path, default=ROOT / "datasets" / "raw" / "oxford102")
    ap.add_argument("--out", type=Path, default=ROOT / "datasets" / "processed" / "oxford102_gallery")
    ap.add_argument("--max-side", type=int, default=640)
    args = ap.parse_args()
    args.raw.mkdir(parents=True, exist_ok=True)
    tgz = fetch("102flowers.tgz", args.raw)
    labels = loadmat(fetch("imagelabels.mat", args.raw))["labels"].ravel()
    setid = loadmat(fetch("setid.mat", args.raw))
    if not (args.raw / "jpg").exists():
        with tarfile.open(tgz) as t:
            safe = [m for m in t.getmembers() if not (m.name.startswith("/") or ".." in Path(m.name).parts)]
            t.extractall(args.raw, members=safe)
    train_ids = set(setid["trnid"].ravel()) | set(setid["valid"].ravel())
    test_ids = set(setid["tstid"].ravel())
    manifest = {"dataset_id": "oxford102", "source": BASE, "citation": "Nilsback & Zisserman (2008), ICVGIP",
                "license": "not stated on the dataset page (research use); images not redistributed in this repo",
                "total_images_in_archive": int(len(labels)), "species": {}}
    rep = ROOT / "datasets" / "reports"
    rep.mkdir(parents=True, exist_ok=True)
    for pair in args.map:
        sp, lab = pair.split("=")
        lab = int(lab)
        idx = np.flatnonzero(labels == lab) + 1  # image_00001.jpg is index 1
        seen, counts, corrupt, dups, thumbs = set(), {"gallery": 0, "test": 0}, 0, 0, []
        for i in idx:
            src = args.raw / "jpg" / f"image_{i:05d}.jpg"
            split = "test" if i in test_ids else ("gallery" if i in train_ids else None)
            if split is None:
                continue
            try:
                im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
            except OSError:
                corrupt += 1
                continue
            h = hashlib.sha1(src.read_bytes()).hexdigest()
            if h in seen:
                dups += 1
                continue
            seen.add(h)
            im.thumbnail((args.max_side, args.max_side))
            d = args.out / (sp if split == "gallery" else f"test/{sp}")
            d.mkdir(parents=True, exist_ok=True)
            im.save(d / src.name, quality=90)
            counts[split] += 1
            if len(thumbs) < 24:
                thumbs.append(ImageOps.fit(im, (64, 64)))
        sheet = Image.new("RGB", (64 * 8, 64 * 3), "white")
        for k, t in enumerate(thumbs):
            sheet.paste(t, ((k % 8) * 64, (k // 8) * 64))
        sheet.save(rep / f"oxford102_contact_{sp}.jpg", quality=75)
        manifest["species"][sp] = {"oxford_label_1based": lab, "images_in_class": int(len(idx)), "gallery_images": counts["gallery"],
                                   "test_images": counts["test"], "corrupt": corrupt, "exact_duplicates_removed": dups,
                                   "contact_sheet": f"datasets/reports/oxford102_contact_{sp}.jpg"}
        print(f"{sp}: label {lab} -> {len(idx)} images (gallery {counts['gallery']}, test {counts['test']})")
    (rep / "oxford102_report.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
