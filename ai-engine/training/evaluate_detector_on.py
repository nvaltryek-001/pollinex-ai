#!/usr/bin/env python3
"""Evaluate the DEPLOYED detector (unchanged, no retraining) on another YOLO-format test split.

    python ai-engine/training/evaluate_detector_on.py --data datasets/processed/tf_flower_detection_sunflower --split test

Measures cross-dataset generalisation honestly (the detector was trained only on USDA orchard blossoms).
Writes ai-engine/reports/detector_on_<dataset>.json.
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
sys.path.insert(0, str(ENGINE))
from pollinex_ai.detector import OnnxYoloDetector, PixelFlowerDetector, load_default_detector  # noqa: E402


EXCLUSIONS = Path(__file__).resolve().parents[2] / "datasets" / "processed" / "leakage_exclusions.txt"


def excluded_stems() -> set[str]:
    """Test images with a near-duplicate in train/val (dataset_quality_audit.py) - skipped in every TEST evaluation."""
    if not EXCLUSIONS.exists():
        return set()
    return {ln.split("#")[0].strip() for ln in EXCLUSIONS.read_text().splitlines() if ln.split("#")[0].strip()}


def image_list(data: Path, split: str) -> list[Path]:
    """Supports both <data>/<split>/images/*.jpg and <data>/<split>.txt (lines './images/x.jpg')."""
    txt = data / f"{split}.txt"
    if txt.exists():
        out = [data / line.strip().removeprefix("./") for line in txt.read_text().splitlines() if line.strip()]
    else:
        out = sorted((data / split / "images").glob("*.jpg"))
    return [p for p in out if p.stem not in excluded_stems()] if split == "test" else out


def label_path(im: Path) -> Path:
    parts = list(im.parts)
    i = len(parts) - 1 - parts[::-1].index("images")
    parts[i] = "labels"
    return Path(*parts).with_suffix(".txt")
from pollinex_ai.metrics import count_errors, detection_report  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--detector", default="default", help="default | pixel | onnx:<path>")
    ap.add_argument("--tag", default="", help="suffix for the report file name")
    args = ap.parse_args()
    if args.detector == "pixel":
        det = PixelFlowerDetector()
    elif args.detector.startswith("onnx:"):
        onnx = Path(args.detector[5:])
        side = onnx.with_suffix(".json")
        cfg = json.loads(side.read_text()) if side.exists() else {}
        det = OnnxYoloDetector(onnx, imgsz=cfg.get("imgsz", 640), names=cfg.get("names"))
    else:
        det = load_default_detector()
    preds, gts, lat = [], [], []
    for im_path in image_list(args.data, args.split):
        rgb = np.array(Image.open(im_path).convert("RGB"))
        H, W = rgb.shape[:2]
        rows = [list(map(float, l.split()[1:])) for l in label_path(im_path).read_text().splitlines() if l.strip()]
        gts.append(np.array([[(x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H] for x, y, w, h in rows], np.float32).reshape(-1, 4))
        t = time.perf_counter()
        res = det.detect(rgb, conf_threshold=0.05) if isinstance(det, OnnxYoloDetector) else det.detect(rgb)
        lat.append((time.perf_counter() - t) * 1000)
        preds.append({"boxes": [d.box for d in res.detections], "scores": [d.score for d in res.detections]})
    rep = detection_report(preds, gts)
    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "detector": det.version, "backend": det.backend,
           "data": str(args.data), "split": args.split, "images": len(gts), "metrics": rep,
           "counting": count_errors([len(p["boxes"]) for p in preds], [len(g) for g in gts]),
           "images_with_zero_predictions": int(sum(len(p["boxes"]) == 0 for p in preds)),
           "latency_ms_mean": float(np.mean(lat)),
           "note": "Deployed detector trained only on USDA apple/peach/pear orchard images; no retraining on this data."
           if args.detector == "default" and det.backend != "yolo11-onnx" else f"detector={args.detector}"}
    name = args.data.name + (f"_{args.tag}" if args.tag else "")
    (ENGINE / "reports" / f"detector_on_{name}.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("images", "images_with_zero_predictions", "latency_ms_mean")}, indent=2),
          {k: round(rep[k], 3) for k in ("mAP50", "mAP50_95", "precision@0.5", "recall@0.5")})


if __name__ == "__main__":
    main()
