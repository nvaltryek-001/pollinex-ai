#!/usr/bin/env python3
"""Extend the open-set species gallery with extra species and evaluate on held-out images.

    python ai-engine/training/extend_gallery.py --extra datasets/processed/oxford102_gallery [--save]

Layout of --extra:  <species>/*.jpg (gallery references)   test/<species>/*.jpg (held out, never added)
Each image is treated as ONE flower crop (close-up photos), centre-cropped to the middle 80 %.

Evaluation (all on held-out data):
  * extra-species test images  -> per-species recall, confusions, unknown rate
  * USDA test flower crops      -> do the original species still work after extension?
  * USDA test background crops  -> open-set rejection after extension
The open-set threshold is NOT re-tuned (it stays the value calibrated on USDA validation data); this is reported.
Writes ai-engine/reports/species_extension_evaluation.json; overwrites models/species_gallery.* only with --save.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ENGINE = Path(__file__).resolve().parents[1]
ROOT = ENGINE.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "training"))
from pollinex_ai.metrics import classification_report  # noqa: E402
from pollinex_ai.species import UNKNOWN, SpeciesGallery, embed_crop  # noqa: E402
from train_species import DATA, background_crops, flower_crops  # noqa: E402

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def centre(img: np.ndarray, frac: float = 0.8) -> np.ndarray:
    h, w = img.shape[:2]
    dh, dw = int(h * (1 - frac) / 2), int(w * (1 - frac) / 2)
    return img[dh:h - dh, dw:w - dw]


def load_dir(d: Path):
    return [(p, np.array(Image.open(p).convert("RGB"))) for p in sorted(d.iterdir()) if p.suffix.lower() in IMG_EXT]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra", type=Path, required=True)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    g = SpeciesGallery.load(ENGINE / "models" / "species_gallery")
    base_counts = g.counts()
    species = sorted(p.name for p in args.extra.iterdir() if p.is_dir() and p.name != "test")
    added = Counter()
    for sp in species:
        for p, img in load_dir(args.extra / sp):
            g.add(sp, centre(img), f"extra:{args.extra.name}/{sp}/{p.name}")
            added[sp] += 1
    test_items = []
    for sp in species:
        tdir = args.extra / "test" / sp
        if tdir.is_dir():
            test_items += [(sp, embed_crop(centre(img))) for _, img in load_dir(tdir)]
    rng = np.random.default_rng(7)
    recs = json.loads((DATA / "records.json").read_text())
    te = [r for r in recs if r["split"] == "test"]
    usda_flowers = flower_crops(te, rng)
    usda_bg = background_crops(te, rng)
    labels = sorted(set(g.labels)) + [UNKNOWN]
    pred = lambda items: [g.predict_vector(v)["species"] for _, v in items]  # noqa: E731
    extra_rep = classification_report([y for y, _ in test_items], pred(test_items), labels)
    usda_rep = classification_report([y for y, _ in usda_flowers], pred(usda_flowers), labels)
    bg_pred = pred(usda_bg)
    per_species = {}
    for sp in species:
        ys = [p for (y, _), p in zip(test_items, pred(test_items)) if y == sp]
        per_species[sp] = {"test_images": len(ys), "recall": float(np.mean([p == sp for p in ys])) if ys else None,
                           "returned_unknown": float(np.mean([p == UNKNOWN for p in ys])) if ys else None,
                           "predicted_as": dict(Counter(ys))}
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "extra_source": str(args.extra.relative_to(ROOT)),
        "threshold_kept": g.threshold, "threshold_note": "not re-tuned; calibrated on USDA validation data",
        "gallery_before": base_counts, "references_added": dict(added), "gallery_after": g.counts(),
        "extra_species_test": per_species, "extra_species_report": extra_rep,
        "usda_test_flowers_after_extension": {"accuracy": usda_rep["accuracy"], "per_class": usda_rep["per_class"]},
        "usda_background_rejection_after_extension": float(np.mean([p == UNKNOWN for p in bg_pred])),
        "saved": bool(args.save),
        "caveat": "Extra references are close-up photos from a different source than the orchard images; accuracy on "
                  "field photos of these species is not measured by this test.",
    }
    (ENGINE / "reports" / "species_extension_evaluation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("references_added", "extra_species_test",
                                              "usda_background_rejection_after_extension")}, indent=2))
    print("USDA flower accuracy after extension:", round(usda_rep["accuracy"], 3))
    if args.save:
        g.meta.update({"extended_at": report["generated_at"], "extended_with": report["extra_source"]})
        g.save(ENGINE / "models" / "species_gallery")
        print("gallery saved")


if __name__ == "__main__":
    main()
