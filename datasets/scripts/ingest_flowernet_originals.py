#!/usr/bin/env python3
"""Ingest ONLY the original (non-augmented) Hibiscus images from FlowerNet (Mendeley 26nvt3t27m v2, MIT).

Download the archive manually from https://data.mendeley.com/datasets/26nvt3t27m and extract it, then:
    python datasets/scripts/ingest_flowernet_originals.py --src /path/to/FlowerNet --species hibiscus

FlowerNet contains 1,400 originals + 5,600 augmented copies. Augmented copies of one photo must not be split
across gallery and test (leakage). This script keeps files under a directory whose name contains 'original'
and additionally drops near-duplicates by perceptual hash.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def dhash(p: Path) -> int:
    g = cv2.resize(np.asarray(Image.open(p).convert("L")), (9, 8), interpolation=cv2.INTER_AREA)
    return int("".join("1" if b else "0" for b in (g[:, 1:] > g[:, :-1]).ravel()), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--species", default="hibiscus")
    ap.add_argument("--out", type=Path, default=ROOT / "datasets" / "processed" / "flowernet_gallery")
    ap.add_argument("--test-fraction", type=float, default=0.25)
    args = ap.parse_args()
    files = [p for p in args.src.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
             and args.species.lower() in str(p).lower() and "original" in str(p.parent).lower()]
    if not files:
        raise SystemExit("No files under an 'original' folder for that species - inspect the archive layout and adapt.")
    seen, keep = [], []
    for f in sorted(files):
        h = dhash(f)
        if all(bin(h ^ s).count("1") > 4 for s in seen):
            seen.append(h)
            keep.append(f)
    random.Random(0).shuffle(keep)
    n_test = int(len(keep) * args.test_fraction)
    for i, f in enumerate(keep):
        d = args.out / (f"test/{args.species}" if i < n_test else args.species)
        d.mkdir(parents=True, exist_ok=True)
        Image.open(f).convert("RGB").save(d / f"{f.stem}.jpg", quality=92)
    print(f"{len(files)} original files -> {len(keep)} after near-duplicate removal; {n_test} held out for test")


if __name__ == "__main__":
    main()
