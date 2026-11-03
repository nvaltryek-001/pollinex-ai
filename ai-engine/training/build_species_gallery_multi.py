#!/usr/bin/env python3
"""Rebuild the open-set species gallery for all species with verified data, gate each species, evaluate once on test.

    python ai-engine/training/build_species_gallery_multi.py [--save]

References (training data only):
  * USDA apple/peach/pear flower crops - train split (CC BY 4.0)
  * TF Flower Detection sunflower close-up crops - train+val split (CC BY 4.0)
  * iNaturalist flowering photos (CC0 / CC BY, species-verified) - train split, all nine species
Validation (threshold + gating): USDA val flowers + USDA val background (-> unknown) + iNaturalist val.
Test (used once, after every choice is fixed): USDA test flowers + background, sunflower close-up test, iNaturalist test.

PRE-REGISTERED GATING RULE (written before any multi-species result existed, 2026-11-03):
  a species is enabled as an AI-supported class only if it has >= 50 reference images AND, on the VALIDATION set,
  recall >= 0.50 and precision >= 0.50. Species failing the rule are removed from the gallery (they stay in the knowledge
  base and simulator, and the user can still select them manually); their test images are still evaluated and should
  come back as 'unknown' or as a wrong species - both are reported.
PRE-REGISTERED EMBEDDING CHOICE (--embed auto, the default): every available embedding (hand-crafted 'hcd-v1' and,
if onnxruntime + models/embed_mnv3l.onnx exist, ImageNet MobileNetV3 'mnv3l-v1') is built with all candidate species,
its threshold tuned on validation, and the one with the higher VALIDATION macro-F1 is used. Test is never consulted.
Writes ai-engine/reports/species_multi_evaluation.json; overwrites models/species_gallery.* only with --save.
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
from pollinex_ai.species import EMBEDDERS, UNKNOWN, SpeciesGallery, cnn_available  # noqa: E402
from train_species import DATA, SEED, background_crops, flower_crops  # noqa: E402

PROC = ROOT / "datasets" / "processed"
INAT = PROC / "inat_flowering"
SUN = PROC / "sunflower_gallery"
MIN_REFS, MIN_RECALL, MIN_PRECISION = 50, 0.50, 0.50
THRESHOLDS = np.round(np.arange(0.30, 0.985, 0.0125), 4)


def centre(img: np.ndarray, frac: float = 0.8) -> np.ndarray:
    h, w = img.shape[:2]
    dh, dw = int(h * (1 - frac) / 2), int(w * (1 - frac) / 2)
    return img[dh:h - dh, dw:w - dw]


def embed_dir(d: Path, label: str, embed) -> list[tuple[str, np.ndarray]]:
    if not d.is_dir():
        return []
    return [(label, embed(centre(np.array(Image.open(p).convert("RGB"))))) for p in sorted(d.glob("*.jpg"))]


def inat(split: str, embed) -> list[tuple[str, np.ndarray]]:
    out = []
    if (INAT / split).is_dir():
        for sp_dir in sorted(p for p in (INAT / split).iterdir() if p.is_dir()):
            out += embed_dir(sp_dir, sp_dir.name, embed)
    return out


def build(refs: list[tuple[str, np.ndarray, str]], keep: set[str] | None = None, version: str = "hcd-v1") -> SpeciesGallery:
    g = SpeciesGallery(EMBEDDERS[version], version)
    for sp, v, src in refs:
        if keep is None or sp in keep:
            g.add_vectors(sp, v[None], src)
    return g


def predict(g, items):
    return [g.predict_vector(v)["species"] for _, v in items]


def tune(g, val, labels):
    rows, best = [], (-1.0, None)
    for t in THRESHOLDS:
        g.threshold = float(t)
        rep = classification_report([y for y, _ in val], predict(g, val), labels)
        rows.append({"threshold": float(t), "val_macro_f1": rep["macro_f1"], "val_accuracy": rep["accuracy"]})
        if rep["macro_f1"] > best[0]:
            best = (rep["macro_f1"], float(t))
    g.threshold = best[1]
    return rows


def load_all(version: str) -> dict:
    embed = EMBEDDERS[version]
    rng = np.random.default_rng(SEED)
    recs = json.loads((DATA / "records.json").read_text())
    usda = {s: [r for r in recs if r["split"] == s] for s in ("train", "val", "test")}
    refs = [(s, v, "usda_fruit_flower:train") for s, v in flower_crops(usda["train"], rng, embed=embed)]
    refs += [(s, v, "tf_flower_detection_sunflower:train+val") for s, v in embed_dir(SUN / "sunflower", "sunflower", embed)]
    refs += [(s, v, "inat_flowering:train") for s, v in inat("train", embed)]
    val = flower_crops(usda["val"], rng, embed=embed) + background_crops(usda["val"], rng, embed=embed) + inat("val", embed)
    test = {"usda_test_flowers": flower_crops(usda["test"], rng, embed=embed),
            "usda_test_background": background_crops(usda["test"], rng, embed=embed),
            "sunflower_closeup_test": embed_dir(SUN / "test" / "sunflower", "sunflower", embed), "inat_test": inat("test", embed)}
    return {"refs": refs, "val": val, "test": test}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--embed", default="auto", choices=["auto", *EMBEDDERS])
    args = ap.parse_args()
    versions = [args.embed] if args.embed != "auto" else [v for v in EMBEDDERS if v == "hcd-v1" or cnn_available()]
    data, selection = {}, {}
    for ver in versions:  # 0) embedding choice on validation (all candidate species)
        data[ver] = load_all(ver)
        cands = sorted({s for s, _, _ in data[ver]["refs"]})
        g0 = build(data[ver]["refs"], version=ver)
        tune(g0, data[ver]["val"], cands + [UNKNOWN])
        r0 = classification_report([y for y, _ in data[ver]["val"]], predict(g0, data[ver]["val"]), cands + [UNKNOWN])
        selection[ver] = {"val_macro_f1": r0["macro_f1"], "val_accuracy": r0["accuracy"], "threshold": g0.threshold}
        print(f"embedding {ver}: val macro-F1 {r0['macro_f1']:.3f} acc {r0['accuracy']:.3f} thr {g0.threshold}")
    version = max(selection, key=lambda v: selection[v]["val_macro_f1"])
    refs, val, test_sets = data[version]["refs"], data[version]["val"], data[version]["test"]
    ref_counts = Counter(s for s, _, _ in refs)
    print("chosen embedding:", version, "| references:", dict(ref_counts), "| val:", dict(Counter(y for y, _ in val)))

    # 1) all candidate species -> threshold on val -> gate on val
    all_species = sorted(ref_counts)
    g = build(refs, version=version)
    tune(g, val, all_species + [UNKNOWN])
    val_rep = classification_report([y for y, _ in val], predict(g, val), all_species + [UNKNOWN])
    gate = {}
    for sp in all_species:
        pc = val_rep["per_class"].get(sp, {})
        ok = ref_counts[sp] >= MIN_REFS and pc.get("recall", 0) >= MIN_RECALL and pc.get("precision", 0) >= MIN_PRECISION
        gate[sp] = {"references": ref_counts[sp], "val_recall": pc.get("recall"), "val_precision": pc.get("precision"),
                    "val_support": pc.get("support"), "enabled": bool(ok)}
    enabled = {sp for sp, v in gate.items() if v["enabled"]}
    print("gating:", {k: (v["enabled"], round(v["val_recall"] or 0, 3), round(v["val_precision"] or 0, 3)) for k, v in gate.items()})

    # 2) final gallery with enabled species only; re-tune threshold on val (unsupported species' val images -> unknown)
    g = build(refs, keep=enabled, version=version)
    labels = sorted(enabled) + [UNKNOWN]
    relabel = lambda items: [(y if y in enabled else UNKNOWN, v) for y, v in items]  # noqa: E731
    tuning = tune(g, relabel(val), labels)
    print(f"threshold {g.threshold}")

    # 3) test, once
    results, all_true, all_pred = {}, [], []
    for name, items in test_sets.items():
        if not items:
            continue
        y_true = [y if y in enabled else UNKNOWN for y, _ in items]
        y_pred = predict(g, items)
        all_true += y_true
        all_pred += y_pred
        results[name] = {"n": len(items), "report": classification_report(y_true, y_pred, labels)}
        if name == "inat_test":
            results[name]["unsupported_species_predicted_as"] = {
                sp: dict(Counter(p for (y, _), p in zip(items, y_pred) if y == sp)) for sp in sorted({y for y, _ in items} - enabled)}
            results[name]["true_species_counts"] = dict(Counter(y for y, _ in items))
    overall = classification_report(all_true, all_pred, labels)
    print(f"TEST overall accuracy {overall['accuracy']:.3f} macro-F1 {overall['macro_f1']:.3f}")
    for k, v in results.items():
        print(f"  {k}: n={v['n']} acc={v['report']['accuracy']:.3f}")

    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "embedding": version, "embedding_selection_on_val": selection, "k": g.k,
              "threshold": g.threshold, "gating_rule": {"min_references": MIN_REFS, "min_val_recall": MIN_RECALL,
                                                        "min_val_precision": MIN_PRECISION, "decided_on": "validation"},
              "gating": gate, "enabled_species": sorted(enabled), "gallery_counts": g.counts(),
              "val_report_all_candidates": val_rep, "threshold_tuning": tuning,
              "test_overall": overall, "test_by_source": results, "saved": bool(args.save),
              "caveat": "iNaturalist photos are whole-scene, user-taken flowering photos (centre crop used); labels are "
                        "image-level species identifications. Test sets were not used for any choice."}
    (ENGINE / "reports" / "species_multi_evaluation.json").write_text(json.dumps(report, indent=2, default=float))
    if args.save:
        g.meta.update({"built_at": report["generated_at"], "seed": SEED, "supported_species": sorted(enabled),
                       "sources": ["usda_fruit_flower train (CC BY 4.0)", "tf_flower_detection sunflower train+val (CC BY 4.0)",
                                   "inat_flowering train (CC0 / CC BY 4.0, per-image attribution)"]})
        g.save(ENGINE / "models" / "species_gallery")
        print("gallery saved")


if __name__ == "__main__":
    main()
