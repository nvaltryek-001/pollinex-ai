#!/usr/bin/env python3
"""Speed / accuracy trade-off for the trained detector, decided on VAL, reported on TEST.

Configurations differ only in inference resolution and pixel-classification stride (same trained model,
same post-processing params rescaled to resolution). Selection rule (fixed before looking at test):
  * full analysis  : fastest config with val mAP50 >= best val mAP50 - 0.02
  * live scanning  : fastest config with val mAP50 >= 0.75 x best val mAP50
The chosen values are written back into the model bundle (params.stride, params.fast_side).
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from PIL import Image

ENGINE = Path(__file__).resolve().parents[1]
ROOT = ENGINE.parent
sys.path.insert(0, str(ENGINE))
from pollinex_ai.detector import PixelFlowerDetector, instances_from_prob  # noqa: E402
from pollinex_ai.metrics import detection_report  # noqa: E402

DATA = ROOT / "datasets" / "processed" / "usda_fruit_flower"
CONFIGS = [(1280, 1), (1280, 2), (960, 2), (800, 2), (640, 2)]


def run(det: PixelFlowerDetector, recs, side, stride):
    p = det.params
    preds, gts, lat = [], [], []
    for r in recs:
        img = np.array(Image.open(DATA / "images" / f"{r['uid']}.jpg").convert("RGB"))
        t = time.perf_counter()
        prob, s = det.probability_map(img, side=side, stride=stride)
        k = side / float(p["work_side"])
        inst = instances_from_prob(prob, p["threshold"], max(2, int(round(p["min_area"] * k * k))), int(round(p["peak_distance"] * k)))
        lat.append((time.perf_counter() - t) * 1000)
        preds.append({"boxes": [[v / s for v in i[0]] for i in inst], "scores": [i[1] for i in inst]})
        gts.append(np.array(r["boxes"], dtype=np.float32).reshape(-1, 4))  # GT in processed-image pixels
    rep = detection_report(preds, gts)
    rep.pop("ap_per_iou")
    return {**rep, "latency_ms_mean": float(np.mean(lat))}


def main():
    path = ENGINE / "models" / "flower_pixel_hgb.joblib"
    det = PixelFlowerDetector(path)
    recs = json.loads((DATA / "records.json").read_text())
    val = [r for r in recs if r["split"] == "val"]
    test = [r for r in recs if r["split"] == "test"]
    rows = []
    for side, stride in CONFIGS:
        v = run(det, val, side, stride)
        rows.append({"side": side, "stride": stride, "val": v})
        print(f"val  side {side} stride {stride}: mAP50 {v['mAP50']:.3f}  {v['latency_ms_mean']:.0f} ms")
    best = max(r["val"]["mAP50"] for r in rows)
    by_speed = sorted(rows, key=lambda r: r["val"]["latency_ms_mean"])
    full = next(r for r in by_speed if r["val"]["mAP50"] >= best - 0.02)
    live = next(r for r in by_speed if r["val"]["mAP50"] >= 0.75 * best)
    for r in rows:
        r["test"] = run(det, test, r["side"], r["stride"])
        print(f"test side {r['side']} stride {r['stride']}: mAP50 {r['test']['mAP50']:.3f} mAP50-95 {r['test']['mAP50_95']:.3f}")
    bundle = joblib.load(path)
    bundle["params"].update({"work_side": full["side"], "stride": full["stride"], "fast_side": live["side"]})
    # NOTE: post-processing params were tuned at the training work_side; they are rescaled at inference.
    bundle["params"].setdefault("tuned_side", 1280)
    bundle["deployed_test_metrics"] = {"full": full["test"], "live": live["test"]}
    joblib.dump(bundle, path, compress=3)
    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "selection_rule": __doc__.strip().splitlines()[3:6],
           "configs": rows, "chosen": {"full": {"side": full["side"], "stride": full["stride"]},
                                       "live": {"side": live["side"], "stride": live["stride"]}}}
    (ENGINE / "reports" / "detector_inference_tradeoff.json").write_text(json.dumps(out, indent=2))
    print("chosen", out["chosen"])


if __name__ == "__main__":
    main()
