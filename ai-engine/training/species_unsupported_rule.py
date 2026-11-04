#!/usr/bin/env python3
"""Should gate-failed species be used as REJECTION references?

    python ai-engine/training/species_unsupported_rule.py          # evaluate on val, report test once, do not save
    python ai-engine/training/species_unsupported_rule.py --save   # write the variant gallery if the rule adopts it

Strawberry failed the pre-registered support gate, so the app must not claim to recognise it. Its photos still landed on
other species (e.g. brinjal, apple). This variant adds strawberry TRAIN photos to the gallery under the label
"__unsupported__:strawberry". When those references win the vote, the answer is "unknown", with the reason "looks like
strawberry, which is not AI-supported". It is never "strawberry".

SELECTION RULE (pre-registered, same objective as species_context_rule.py):
  objective = mean validation macro-F1 over the AUTO setting (deployed detector, crop/scene blend from species_context.json)
  and the CLOSE-UP setting (centre crops + USDA background crops). Labels: 8 enabled species + unknown; strawberry = unknown.
  Adopt only if the variant's validation objective is higher than the current gallery's.
Test is evaluated once for both galleries and reported whatever the outcome.
Writes ai-engine/reports/species_unsupported_rule.json.
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
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "training"))
from pollinex_ai.detector import load_default_detector  # noqa: E402
from pollinex_ai.pipeline import GALLERY_PATH, MODELS_DIR  # noqa: E402
from pollinex_ai.species import UNKNOWN, UNSUPPORTED_PREFIX, SpeciesGallery  # noqa: E402
from species_context_rule import PROC, centre, items, score_auto, score_close  # noqa: E402

UNSUPPORTED = ["strawberry"]


def variant(g: SpeciesGallery) -> tuple[SpeciesGallery, int]:
    v = SpeciesGallery.load(GALLERY_PATH)
    n = 0
    for sp in UNSUPPORTED:
        for root in (PROC / "inat_flowering", PROC / "commons_flowers"):
            for p in sorted((root / "train" / sp).glob("*.jpg")):
                v.add_vectors(UNSUPPORTED_PREFIX + sp, g.embed_fn(centre(np.array(Image.open(p).convert("RGB"))))[None],
                              f"{root.name}:train (rejection reference)")
                n += 1
    v.meta = {**v.meta, "rejection_species": UNSUPPORTED}
    return v, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    ctx = json.loads((MODELS_DIR / "species_context.json").read_text())
    a, t = ctx["crop_weight"], ctx.get("abstain_share", 0.0)
    det = load_default_detector()
    cur = SpeciesGallery.load(GALLERY_PATH)
    var, n_ref = variant(cur)
    labels = cur.species + [UNKNOWN]
    res = {}
    for name, g in (("current", cur), ("with_rejection_refs", var)):
        va_auto, va_close = items("val", g, det)
        ra, rc = score_auto(g, va_auto, a, t, labels), score_close(g, va_close, t, labels)
        res[name] = {"val_objective": (ra["macro_f1"] + rc["macro_f1"]) / 2, "val_auto": ra["macro_f1"], "val_closeup": rc["macro_f1"]}
        print(name, res[name], flush=True)
    adopt = res["with_rejection_refs"]["val_objective"] > res["current"]["val_objective"]
    print("adopt:", adopt, flush=True)
    for name, g in (("current", cur), ("with_rejection_refs", var)):
        te_auto, te_close = items("test", g, det)
        ra, rc = score_auto(g, te_auto, a, t, labels), score_close(g, te_close, t, labels)
        res[name]["test"] = {s: {"accuracy": r["accuracy"], "macro_f1": r["macro_f1"],
                                 "unknown_recall": r["per_class"][UNKNOWN]["recall"],
                                 "per_class": r["per_class"], "confusion_matrix": r["confusion_matrix"]}
                             for s, r in (("auto", ra), ("closeup", rc))}
        print(name, "test", {s: {k: round(v, 3) for k, v in d.items() if k in ("accuracy", "macro_f1", "unknown_recall")}
                             for s, d in res[name]["test"].items()}, flush=True)
    out = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rejection_species": UNSUPPORTED,
           "rejection_references": n_ref, "crop_weight": a, "labels": labels, "results": res, "adopted": adopt}
    (ENGINE / "reports" / "species_unsupported_rule.json").write_text(json.dumps(out, indent=2))
    if args.save and adopt:
        var.save(GALLERY_PATH)
        print("saved the variant gallery to", GALLERY_PATH)


if __name__ == "__main__":
    main()
