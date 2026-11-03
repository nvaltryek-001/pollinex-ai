#!/usr/bin/env python3
"""Build species *reference-gallery* folders (classification only) from Oxford 102 Flowers.

Oxford-102 has image-level labels only - it can extend the open-set species gallery but must NEVER be used
as detector training data. Class indices for the wanted species are passed explicitly and a contact sheet
is written so you can visually verify the mapping before using it.

    python datasets/scripts/download_oxford102_subset.py --map sunflower=54 hibiscus=83
    # inspect datasets/reports/oxford102_contact_<species>.jpg, then:
    python ai-engine/training/train_species.py --extra-gallery datasets/processed/oxford102_gallery

Uses the official setid.mat split: 'trnid' -> gallery, 'tstid' -> held-out test folder (never in the gallery).
"""
from __future__ import annotations

import argparse
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://www.robots.ox.ac.uk/~vgg/data/flowers/102/"


def fetch(name: str, dest: Path) -> Path:
    p = dest / name
    if not p.exists():
        print("downloading", BASE + name)
        urllib.request.urlretrieve(BASE + name, p)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", nargs="+", required=True, help="species_id=oxford_label (1-based), e.g. sunflower=54")
    ap.add_argument("--raw", type=Path, default=ROOT / "datasets" / "raw" / "oxford102")
    ap.add_argument("--out", type=Path, default=ROOT / "datasets" / "processed" / "oxford102_gallery")
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
    for pair in args.map:
        sp, lab = pair.split("=")
        lab = int(lab)
        idx = np.flatnonzero(labels == lab) + 1  # image_00001.jpg is index 1
        thumbs = []
        for i in idx:
            src = args.raw / "jpg" / f"image_{i:05d}.jpg"
            split = "test" if i in test_ids else ("gallery" if i in train_ids else None)
            if split is None:
                continue
            d = args.out / (sp if split == "gallery" else f"test/{sp}")
            d.mkdir(parents=True, exist_ok=True)
            im = Image.open(src).convert("RGB")
            im.save(d / src.name, quality=92)
            if len(thumbs) < 24:
                thumbs.append(im.resize((128, 128)))
        sheet = Image.new("RGB", (128 * 6, 128 * 4), "white")
        for k, t in enumerate(thumbs):
            sheet.paste(t, ((k % 6) * 128, (k // 6) * 128))
        sheet.save(ROOT / "datasets" / "reports" / f"oxford102_contact_{sp}.jpg")
        print(f"{sp}: label {lab} -> {len(idx)} images; verify datasets/reports/oxford102_contact_{sp}.jpg")


if __name__ == "__main__":
    main()
