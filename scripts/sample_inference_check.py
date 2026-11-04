#!/usr/bin/env python3
"""Run the full deployed pipeline (detector -> species gallery -> heuristics -> readiness rules) on real held-out TEST
photos of every one of the nine species, and record what each stage returned and by which method.

    python scripts/sample_inference_check.py [--per-species 5]

Writes ai-engine/reports/sample_inference_check_<mode>.json. This is a smoke check of real inference end to end. It is not an
accuracy evaluation; for metrics see scripts/evaluate_deployed_models.py.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai-engine"))
from pollinex_ai.pipeline import Analyzer  # noqa: E402

PROC = ROOT / "datasets" / "processed"
SPECIES = ["apple", "peach", "pear", "sunflower", "hibiscus", "tomato", "strawberry", "brinjal", "chilli"]


def test_photos(sp: str, n: int) -> list[Path]:
    out: list[Path] = []
    for root in (PROC / "inat_flowering" / "test" / sp, PROC / "commons_flowers" / "test" / sp):
        out += sorted(root.glob("*.jpg")) if root.is_dir() else []
    return out[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-species", type=int, default=5)
    ap.add_argument("--mode", default="auto", choices=["auto", "closeup"])
    args = ap.parse_args()
    an = Analyzer()
    info = an.model_info()
    rows, summary = [], {}
    for sp in SPECIES:
        preds, methods = Counter(), Counter()
        for p in test_photos(sp, args.per_species):
            rgb = np.array(Image.open(p).convert("RGB"))
            t = time.perf_counter()
            r = an.analyze(rgb, mode=args.mode)
            ms = (time.perf_counter() - t) * 1000
            f0 = r["flowers"][0] if r["flowers"] else None
            row = {"true_species": sp, "file": str(p.relative_to(ROOT)), "detection_method": r["detection_method"],
                   "flower_count": r["flower_count"], "latency_ms": round(ms),
                   "top_species": f0["species"]["species"] if f0 else None,
                   "top_species_confidence": round(f0["species"].get("confidence", 0.0), 3) if f0 else None,
                   "species_method": f0["species"].get("method") if f0 else None,
                   "stage_method": (f0.get("stage") or {}).get("method") if f0 else None,
                   "readiness": (f0.get("readiness") or {}).get("category") if f0 else None,
                   "readiness_method": (f0.get("readiness") or {}).get("method") if f0 else None,
                   "warnings": r["warnings"]}
            rows.append(row)
            preds[row["top_species"]] += 1
            methods[row["detection_method"]] += 1
        summary[sp] = {"photos": sum(preds.values()), "top_species_predictions": dict(preds), "detection_methods": dict(methods),
                       "top_species_matches_label": preds.get(sp, 0)}
        print(f"{sp:10s} {summary[sp]}")
    out = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "mode": args.mode, "model": info,
           "note": "Real held-out test photos (iNaturalist / Commons), full pipeline. Detection boxes exist only for "
                   "apple, peach, pear and sunflower; for other species the detector is untrained, so close-up fallback is expected. "
                   "Stage/structure/health are heuristics and readiness is rule-based; their method fields are recorded per image.",
           "summary": summary, "images": rows}
    (ROOT / "ai-engine" / "reports" / f"sample_inference_check_{args.mode}.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"wrote ai-engine/reports/sample_inference_check_{args.mode}.json")


if __name__ == "__main__":
    main()
