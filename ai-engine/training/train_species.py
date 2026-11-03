#!/usr/bin/env python3
"""Build + evaluate the open-set species reference gallery.

Gallery = TRAIN-split flower crops (apple / peach / pear from the USDA set).
Open-set threshold = chosen on VAL to maximise macro-F1 over {apple, peach, pear, unknown},
where 'unknown' queries are background crops (non-flower regions) from VAL images.
TEST is evaluated once:
  * closed-set + open-set confusion matrix
  * background-crop rejection rate
  * leave-one-species-out: gallery WITHOUT species S, queries of S should come back 'unknown'

CAVEAT (also written into the report): each species was photographed with a different camera setup,
so species identity is confounded with capture conditions in this data.

Optional: --extra-gallery DIR adds reference images arranged as DIR/<species_id>/*.jpg (e.g. built with
datasets/scripts/download_oxford102_subset.py on a machine with internet). Those species are not
evaluated unless DIR also contains a held-out 'test' subfolder per species.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ENGINE = Path(__file__).resolve().parents[1]
ROOT = ENGINE.parent
sys.path.insert(0, str(ENGINE))
from pollinex_ai.metrics import classification_report  # noqa: E402
from pollinex_ai.species import UNKNOWN, SpeciesGallery, crop_box, embed_crop  # noqa: E402

DATA = ROOT / "datasets" / "processed" / "usda_fruit_flower"
SEED = 7
MIN_SIDE = 14
MAX_PER_IMAGE = 40


def flower_crops(records, rng):
    out = []
    for r in records:
        img = np.array(Image.open(DATA / "images" / f"{r['uid']}.jpg").convert("RGB"))
        boxes = [b for b in r["boxes"] if min(b[2] - b[0], b[3] - b[1]) >= MIN_SIDE]
        if len(boxes) > MAX_PER_IMAGE:
            boxes = [boxes[i] for i in rng.choice(len(boxes), MAX_PER_IMAGE, replace=False)]
        out += [(r["species"], embed_crop(crop_box(img, b))) for b in boxes]
    return out


def background_crops(records, rng, per_image=10):
    out = []
    for r in records:
        img = np.array(Image.open(DATA / "images" / f"{r['uid']}.jpg").convert("RGB"))
        mask = np.array(Image.open(DATA / "masks" / f"{r['uid']}.png")) > 0
        H, W = mask.shape
        got, tries = 0, 0
        while got < per_image and tries < 200:
            tries += 1
            s = int(rng.integers(24, 64))
            x, y = int(rng.integers(0, W - s)), int(rng.integers(0, H - s))
            if mask[y:y + s, x:x + s].mean() < 0.01:
                out.append((UNKNOWN, embed_crop(img[y:y + s, x:x + s])))
                got += 1
    return out


def build(train, exclude=None, k=7):
    g = SpeciesGallery()
    g.k = k
    for sp, v in train:
        if sp != exclude:
            g.add_vectors(sp, v[None], "usda_fruit_flower:train")
    return g


def predict_all(g, items):
    return [g.predict_vector(v)["species"] for _, v in items]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra-gallery", type=Path, default=None)
    args = ap.parse_args()
    rng = np.random.default_rng(SEED)
    recs = json.loads((DATA / "records.json").read_text())
    split = {s: [r for r in recs if r["split"] == s] for s in ("train", "val", "test")}
    tr = flower_crops(split["train"], rng)
    va = flower_crops(split["val"], rng) + background_crops(split["val"], rng)
    te_f = flower_crops(split["test"], rng)
    te_b = background_crops(split["test"], rng)
    print(f"gallery {len(tr)}  val {len(va)}  test flowers {len(te_f)}  test background {len(te_b)}")

    labels = ["apple", "peach", "pear", UNKNOWN]
    g = build(tr)
    tune_rows, best = [], (-1, None)
    for thr in np.round(np.arange(0.55, 0.96, 0.025), 3):
        g.threshold = float(thr)
        rep = classification_report([y for y, _ in va], predict_all(g, va), labels)
        tune_rows.append({"threshold": float(thr), "val_macro_f1": rep["macro_f1"], "val_accuracy": rep["accuracy"]})
        if rep["macro_f1"] > best[0]:
            best = (rep["macro_f1"], float(thr))
    g.threshold = best[1]
    print(f"chosen open-set threshold {g.threshold} (val macro-F1 {best[0]:.3f})")

    te = te_f + te_b
    test_rep = classification_report([y for y, _ in te], predict_all(g, te), labels)
    closed = classification_report([y for y, _ in te_f], predict_all(g, te_f), labels)
    bg_pred = predict_all(g, te_b)
    loso = {}
    for sp in ("apple", "peach", "pear"):
        g2 = build(tr, exclude=sp)
        g2.threshold = g.threshold
        q = [x for x in te_f if x[0] == sp]
        preds = predict_all(g2, q)
        loso[sp] = {"queries": len(q), "returned_unknown_fraction": float(np.mean([p == UNKNOWN for p in preds])),
                    "wrongly_assigned_to": {p: preds.count(p) for p in set(preds) if p != UNKNOWN}}
    print(f"TEST open-set acc {test_rep['accuracy']:.3f} macro-F1 {test_rep['macro_f1']:.3f} | flowers-only acc "
          f"{closed['accuracy']:.3f} | background rejected {np.mean([p == UNKNOWN for p in bg_pred]):.3f}")
    print("leave-one-species-out:", {k: round(v["returned_unknown_fraction"], 3) for k, v in loso.items()})

    if args.extra_gallery and args.extra_gallery.exists():
        for sp_dir in sorted(p for p in args.extra_gallery.iterdir() if p.is_dir()):
            for f in sorted(sp_dir.glob("*.jp*g"))[:200]:
                g.add(sp_dir.name, np.array(Image.open(f).convert("RGB")), f"extra:{f.name}")
    g.meta.update({"built_at": datetime.now(timezone.utc).isoformat(), "seed": SEED,
                   "sources": ["usda_fruit_flower train split (CC BY 4.0)"]})
    g.save(ENGINE / "models" / "species_gallery")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "embedding": "hand-crafted hcd-v1 (HSV hist + Lab moments + HOG + LBP)",
        "k": g.k, "threshold": g.threshold, "gallery_counts": g.counts(),
        "data": {"gallery_crops": len(tr), "val_queries": len(va), "test_flower_crops": len(te_f), "test_background_crops": len(te_b)},
        "test_open_set": test_rep, "test_flowers_only": closed,
        "test_background_rejection_rate": float(np.mean([p == UNKNOWN for p in bg_pred])),
        "leave_one_species_out": loso, "threshold_tuning": tune_rows,
        "caveat": "Species and camera setup are confounded in this dataset (one setup per species). High accuracy here "
                  "does not demonstrate field-general species recognition; it demonstrates the gallery + open-set mechanism.",
    }
    (ENGINE / "reports" / "species_evaluation.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
