#!/usr/bin/env python3
"""Select how the pipeline turns gallery votes into a species answer.

The selection uses VALIDATION data only; TEST is evaluated once, after the choice is fixed. Nothing is retrained: the
deployed detector and gallery are used unchanged.

    python ai-engine/training/species_context_rule.py            # select on val, report test, do not save
    python ai-engine/training/species_context_rule.py --save     # also write ai-engine/models/species_context.json

PROBLEM (found by scripts/sample_inference_check.py): in auto mode each flower is classified from its padded detection
box only. On whole-scene photos the top box is often small or off-centre, so auto mode was weaker than close-up mode. The
gallery also rarely says "unknown" for species it does not support (e.g. strawberry).

CANDIDATES (fixed before any results were seen):
  * crop_weight a in {1.0 (current), 0.75, 0.5, 0.25, 0.0}: the final vote distribution for a detected flower is
    a * votes(box crop) + (1 - a) * votes(centre-80 % of the whole photo). Close-up mode is unchanged by a (crop == scene).
  * abstain_share t in {0 (current), 0.40, 0.45, 0.50, 0.55, 0.60}: if the top species' share of the fused votes is below t,
    the answer is "unknown" (abstain) instead of a low-confidence species.

SELECTION RULE (pre-registered):
  1. a: highest validation macro-F1 of the top flower's species in AUTO mode (t = 0).
  2. t: with a fixed, highest mean validation macro-F1 over the AUTO setting and the CLOSE-UP setting. The close-up setting
     also contains USDA validation background crops, whose correct answer is "unknown", so abstaining is not free.
  3. Ties go to the value closer to the current behaviour (a = 1, t = 0).
  4. Deploy (--save) only if the selected rule beats the current rule (a = 1, t = 0) on that validation objective.
Labels: the 8 enabled gallery species + "unknown"; photos of species not enabled in the gallery (strawberry) count as "unknown".

Writes ai-engine/reports/species_context_rule.json.
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
sys.path.insert(0, str(ENGINE / "training"))
from pollinex_ai.detector import load_default_detector  # noqa: E402
from pollinex_ai.metrics import classification_report  # noqa: E402
from pollinex_ai.pipeline import GALLERY_PATH  # noqa: E402
from pollinex_ai.species import UNKNOWN, SpeciesGallery, crop_box, is_reject_label  # noqa: E402
from evaluate_detector_on import excluded_stems  # noqa: E402
from train_species import DATA, SEED, background_crops  # noqa: E402

PROC = ROOT / "datasets" / "processed"
CROP_WEIGHTS = [1.0, 0.75, 0.5, 0.25, 0.0]
ABSTAIN = [0.0, 0.40, 0.45, 0.50, 0.55, 0.60]


def centre(img: np.ndarray, frac: float = 0.8) -> np.ndarray:
    h, w = img.shape[:2]
    dh, dw = int(h * (1 - frac) / 2), int(w * (1 - frac) / 2)
    return img[dh:h - dh, dw:w - dw]


def votes(g: SpeciesGallery, v: np.ndarray) -> tuple[dict[str, float], float]:
    ranked, best = g._scores(v)
    return dict(ranked), best


def decide(g: SpeciesGallery, dist: dict[str, float], best_sim: float, t: float) -> str:
    """Same logic as SpeciesGallery.predict_vector, applied to a (possibly fused) vote distribution, plus abstention."""
    if not dist or best_sim < g.threshold:
        return UNKNOWN
    sp, share = max(dist.items(), key=lambda kv: kv[1])
    if is_reject_label(sp) or share < t:
        return UNKNOWN
    return sp


def fuse(a: float, crop: dict, scene: dict) -> dict:
    keys = set(crop) | set(scene)
    return {k: a * crop.get(k, 0.0) + (1 - a) * scene.get(k, 0.0) for k in keys}


def photos(split: str) -> list[tuple[str, Path]]:
    out, skip = [], excluded_stems() if split == "test" else set()
    for root in (PROC / "inat_flowering", PROC / "commons_flowers"):
        d = root / split
        for sp_dir in sorted(p for p in d.iterdir() if p.is_dir()) if d.is_dir() else []:
            out += [(sp_dir.name, p) for p in sorted(sp_dir.glob("*.jpg")) if p.stem not in skip]
    recs = json.loads((DATA / "records.json").read_text())
    out += [(r["species"], DATA / "images" / f"{r['uid']}.jpg") for r in recs if r["split"] == split]
    return out


def items(split: str, g, det) -> tuple[list[dict], list[dict]]:
    """Per photo: true label, auto-mode top-flower crop votes (or None = close-up fallback), scene votes."""
    auto, close = [], []
    enabled = set(g.species)
    for sp, p in photos(split):
        y = sp if sp in enabled else UNKNOWN
        rgb = np.array(Image.open(p).convert("RGB"))
        scene_d, scene_b = votes(g, g.embed_fn(centre(rgb)))
        dets = [d for d in det.detect(rgb).detections if not d.low_confidence]
        crop_d, crop_b = (votes(g, g.embed_fn(crop_box(rgb, dets[0].box, pad=0.1))) if dets else (None, None))
        auto.append({"y": y, "crop": crop_d, "crop_best": crop_b, "scene": scene_d, "scene_best": scene_b})
        close.append({"y": y, "crop": scene_d, "crop_best": scene_b})
    recs = [r for r in json.loads((DATA / "records.json").read_text()) if r["split"] == split]
    for _, v in background_crops(recs, np.random.default_rng(SEED), embed=g.embed_fn):
        d, b = votes(g, v)
        close.append({"y": UNKNOWN, "crop": d, "crop_best": b})
    return auto, close


def score_auto(g, rows, a, t, labels):
    yp = []
    for r in rows:
        if r["crop"] is None:  # no confident detection -> close-up fallback on the whole frame
            yp.append(decide(g, r["scene"], r["scene_best"], t))
        else:
            yp.append(decide(g, fuse(a, r["crop"], r["scene"]), max(r["crop_best"], r["scene_best"]) if a < 1 else r["crop_best"], t))
    return classification_report([r["y"] for r in rows], yp, labels)


def score_close(g, rows, t, labels):
    return classification_report([r["y"] for r in rows], [decide(g, r["crop"], r["crop_best"], t) for r in rows], labels)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    g = SpeciesGallery.load(GALLERY_PATH)
    det = load_default_detector()
    labels = sorted(set(g.species)) + [UNKNOWN]
    print("embedding validation photos ...", flush=True)
    va_auto, va_close = items("val", g, det)
    grid_a = {a: score_auto(g, va_auto, a, 0.0, labels)["macro_f1"] for a in CROP_WEIGHTS}
    best_a = max(CROP_WEIGHTS, key=lambda a: (round(grid_a[a], 6), a))  # tie -> larger a (closer to current)
    grid_t = {t: (score_auto(g, va_auto, best_a, t, labels)["macro_f1"] + score_close(g, va_close, t, labels)["macro_f1"]) / 2
              for t in ABSTAIN}
    best_t = max(ABSTAIN, key=lambda t: (round(grid_t[t], 6), -t))  # tie -> smaller t
    current_obj = (score_auto(g, va_auto, 1.0, 0.0, labels)["macro_f1"] + score_close(g, va_close, 0.0, labels)["macro_f1"]) / 2
    selected_obj = grid_t[best_t]
    adopt = selected_obj > current_obj
    print(f"val: crop_weight grid {grid_a} -> {best_a}; abstain grid {grid_t} -> {best_t}; "
          f"objective current {current_obj:.4f} selected {selected_obj:.4f} adopt={adopt}", flush=True)

    print("embedding test photos (used once) ...", flush=True)
    te_auto, te_close = items("test", g, det)

    def both(a, t):
        ra, rc = score_auto(g, te_auto, a, t, labels), score_close(g, te_close, t, labels)
        keep = ("accuracy", "macro_f1", "per_class", "labels", "confusion_matrix")
        return {"auto": {k: ra[k] for k in keep}, "closeup": {k: rc[k] for k in keep}}

    test_cur, test_sel = both(1.0, 0.0), both(best_a, best_t)
    for name, r in (("current", test_cur), ("selected", test_sel)):
        print(f"test {name}: auto acc {r['auto']['accuracy']:.3f} F1 {r['auto']['macro_f1']:.3f} | "
              f"close-up acc {r['closeup']['accuracy']:.3f} F1 {r['closeup']['macro_f1']:.3f} | "
              f"unknown recall auto {r['auto']['per_class'][UNKNOWN]['recall']:.3f} close {r['closeup']['per_class'][UNKNOWN]['recall']:.3f}")
    out = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "rule": __doc__.split("SELECTION RULE (pre-registered):")[1].split("Writes")[0].strip(),
           "val_items": {"auto_photos": len(va_auto), "closeup_items": len(va_close)},
           "test_items": {"auto_photos": len(te_auto), "closeup_items": len(te_close)},
           "val_crop_weight_macro_f1": grid_a, "val_abstain_objective": grid_t,
           "selected": {"crop_weight": best_a, "abstain_share": best_t}, "val_objective_current": current_obj,
           "val_objective_selected": selected_obj, "adopted": adopt, "test_current": test_cur, "test_selected": test_sel,
           "note": "Top-flower species per photo. Auto setting = full-scene photos through the deployed detector; close-up "
                   "setting = centre crop of the same photos plus USDA background crops. Strawberry counts as unknown."}
    (ENGINE / "reports" / "species_context_rule.json").write_text(json.dumps(out, indent=2))
    if args.save and adopt:
        (ENGINE / "models" / "species_context.json").write_text(json.dumps({
            "crop_weight": best_a, "abstain_share": best_t, "selected_on": "validation",
            "report": "ai-engine/reports/species_context_rule.json", "generated_at": out["generated_at"]}, indent=2))
        print("saved ai-engine/models/species_context.json")
    elif args.save:
        print("not saved: the selected rule does not beat the current rule on validation")


if __name__ == "__main__":
    main()
