#!/usr/bin/env python3
"""Detailed detector analysis: per-species metrics, confidence-threshold sweep, error analysis, latency.

    python ai-engine/training/detector_analysis.py --detector onnx:ai-engine/models/flower_yolo11n.onnx --split val
    python ai-engine/training/detector_analysis.py --detector onnx:... --split test --threshold-from val

Data: every committed box-annotated set - USDA (apple/peach/pear; species from the file name) and the TF sunflower subset.
Outputs ai-engine/reports/detector_analysis_<tag>_<split>.json with, per species and overall:
  mAP@0.5, mAP@0.5:0.95, and at each confidence threshold 0.05..0.90: precision, recall, F1, TP/FP/FN (IoU 0.5);
  recall by box size (small < 32^2, medium < 96^2, large, in original pixels); count error; latency p50/p90.
--split val chooses the OPERATING THRESHOLD = argmax overall F1 on validation (pre-registered rule) and stores it.
--threshold-from val reads that threshold and reports the test split at it (test is never used to choose it).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ENGINE = Path(__file__).resolve().parents[1]
ROOT = ENGINE.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "training"))
from evaluate_detector_on import image_list, label_path  # noqa: E402
from pollinex_ai.detector import OnnxYoloDetector, PixelFlowerDetector  # noqa: E402
from pollinex_ai.metrics import detection_report, iou_matrix  # noqa: E402

PROC = ROOT / "datasets" / "processed"
SETS = {"usda": PROC / "usda_fruit_flower", "sunflower": PROC / "tf_flower_detection_sunflower"}
THRESHOLDS = [round(x, 2) for x in np.arange(0.05, 0.91, 0.05)]


def species_of(set_name: str, im: Path) -> str:
    return "sunflower" if set_name == "sunflower" else im.stem.split("_")[0]


def load_gt(im: Path, W: int, H: int) -> np.ndarray:
    rows = [list(map(float, ln.split()[1:])) for ln in label_path(im).read_text().splitlines() if ln.strip()]
    return np.array([[(x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H] for x, y, w, h in rows],
                    np.float32).reshape(-1, 4)


def prf_at(items, thr: float) -> dict:
    tp = fp = fn = 0
    for p, g in items:
        keep = np.asarray(p["scores"]) >= thr
        boxes = np.asarray(p["boxes"], np.float32).reshape(-1, 4)[keep]
        scores = np.asarray(p["scores"])[keep]
        if len(boxes) == 0:
            fn += len(g)
            continue
        if len(g) == 0:
            fp += len(boxes)
            continue
        ious = iou_matrix(boxes[np.argsort(-scores)], g)
        used = np.zeros(len(g), bool)
        for row in ious:
            row = np.where(used, -1, row)
            j = int(row.argmax())
            if row[j] >= 0.5:
                used[j] = True
                tp += 1
            else:
                fp += 1
        fn += int((~used).sum())
    p = tp / max(tp + fp, 1)
    r = tp / max(tp + fn, 1)
    return {"threshold": thr, "precision": p, "recall": r, "f1": 2 * p * r / max(p + r, 1e-9), "tp": tp, "fp": fp, "fn": fn}


def size_recall(items, thr: float) -> dict:
    buckets = {"small": [0, 0], "medium": [0, 0], "large": [0, 0]}
    for p, g in items:
        keep = np.asarray(p["scores"]) >= thr
        boxes = np.asarray(p["boxes"], np.float32).reshape(-1, 4)[keep]
        ious = iou_matrix(g, boxes) if len(boxes) and len(g) else np.zeros((len(g), 0))
        for k, gb in enumerate(g):
            a = (gb[2] - gb[0]) * (gb[3] - gb[1])
            b = "small" if a < 32 ** 2 else "medium" if a < 96 ** 2 else "large"
            buckets[b][1] += 1
            buckets[b][0] += int(ious.shape[1] > 0 and ious[k].max() >= 0.5)
    return {k: {"n_gt": n, "recall": hit / n if n else None} for k, (hit, n) in buckets.items()}


def summarise(items, thr_fixed: float | None) -> dict:
    preds, gts = [p for p, _ in items], [g for _, g in items]
    rep = detection_report(preds, gts)
    sweep = [prf_at(items, t) for t in THRESHOLDS]
    out = {"images": len(items), "gt_boxes": int(sum(len(g) for g in gts)), "mAP50": rep["mAP50"], "mAP50_95": rep["mAP50_95"],
           "threshold_sweep": sweep}
    if thr_fixed is not None:
        out["at_operating_threshold"] = prf_at(items, thr_fixed)
        out["recall_by_size_at_operating_threshold"] = size_recall(items, thr_fixed)
        cnt = [int((np.asarray(p["scores"]) >= thr_fixed).sum()) for p in preds]
        out["count_MAE_at_operating_threshold"] = float(np.mean([abs(c - len(g)) for c, g in zip(cnt, gts)]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detector", required=True, help="pixel | onnx:<path>")
    ap.add_argument("--split", default="val")
    ap.add_argument("--threshold-from", default=None, help="split whose saved operating threshold is used")
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()
    if args.detector == "pixel":
        det, tag = PixelFlowerDetector(), args.tag or "pixel"
    else:
        onnx = Path(args.detector[5:])
        cfg = json.loads(onnx.with_suffix(".json").read_text()) if onnx.with_suffix(".json").exists() else {}
        det, tag = OnnxYoloDetector(onnx, imgsz=cfg.get("imgsz", 640), names=cfg.get("names")), args.tag or "yolo11"
    per_sp, lat = {}, []
    for set_name, root in SETS.items():
        for im in image_list(root, args.split):
            rgb = np.array(Image.open(im).convert("RGB"))
            H, W = rgb.shape[:2]
            t = time.perf_counter()
            res = det.detect(rgb, conf_threshold=0.05) if isinstance(det, OnnxYoloDetector) else det.detect(rgb)
            lat.append((time.perf_counter() - t) * 1000)
            pred = {"boxes": [d.box for d in res.detections], "scores": [d.score for d in res.detections]}
            per_sp.setdefault(species_of(set_name, im), []).append((pred, load_gt(im, W, H)))
    thr = None
    if args.threshold_from:
        thr = json.loads((ENGINE / "reports" / f"detector_analysis_{tag}_{args.threshold_from}.json").read_text())["operating_threshold"]
    everything = [x for v in per_sp.values() for x in v]
    overall = summarise(everything, thr)
    if thr is None:
        best = max(overall["threshold_sweep"], key=lambda r: r["f1"])
        thr = best["threshold"]
        overall = summarise(everything, thr)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "detector": args.detector, "split": args.split,
              "operating_threshold": thr,
              "threshold_rule": "argmax overall F1 (IoU 0.5) on the validation split; test reported at that threshold",
              "threshold_source": args.threshold_from or args.split,
              "overall": overall, "per_species": {sp: summarise(v, thr) for sp, v in sorted(per_sp.items())},
              "latency_ms": {"mean": float(np.mean(lat)), "p50": float(np.percentile(lat, 50)), "p90": float(np.percentile(lat, 90))}}
    out = ENGINE / "reports" / f"detector_analysis_{tag}_{args.split}.json"
    out.write_text(json.dumps(report, indent=2))
    o = report["overall"]["at_operating_threshold"]
    print(f"{tag} {args.split}: thr {thr} P {o['precision']:.3f} R {o['recall']:.3f} F1 {o['f1']:.3f} mAP50 {overall['mAP50']:.3f}")
    for sp, v in report["per_species"].items():
        a = v["at_operating_threshold"]
        print(f"  {sp:10s} n={v['images']:3d} gt={v['gt_boxes']:5d} mAP50 {v['mAP50']:.3f} mAP50-95 {v['mAP50_95']:.3f} "
              f"P {a['precision']:.3f} R {a['recall']:.3f} F1 {a['f1']:.3f}")


if __name__ == "__main__":
    main()
