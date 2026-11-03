#!/usr/bin/env python3
"""YOLO11 fine-tuning recipe (Ultralytics, AGPL-3.0) -> ONNX for the backend.

NOT RUN in the original build environment: PyTorch/Ultralytics could not be installed there (package
registries blocked). Run on a laptop/GPU box:

    pip install -r ai-engine/requirements-train.txt
    python ai-engine/training/train_yolo11.py --data datasets/processed/usda_fruit_flower/data.yaml
    python ai-engine/training/train_yolo11.py --data ... --evaluate-only --weights runs/.../best.pt

The script evaluates on the TEST split once, writes ai-engine/reports/yolo11_evaluation.json, and exports
ai-engine/models/flower_yolo11n.onnx, which the backend then prefers over the CPU pixel model.

Licence note: Ultralytics is AGPL-3.0. Distributing a service built on it may require releasing source under
AGPL or obtaining an Ultralytics enterprise licence. The default CPU detector has no such dependency.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="YOLO data.yaml (train/val/test)")
    ap.add_argument("--model", default="yolo11n.pt")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=1280, help="flowers are small; keep resolution high")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default=None, help="'cpu', '0', ...")
    ap.add_argument("--weights", default=None)
    ap.add_argument("--evaluate-only", action="store_true")
    ap.add_argument("--seed", type=int, default=20261102)
    args = ap.parse_args()

    from ultralytics import YOLO  # imported here so the rest of the repo never needs torch

    if not args.evaluate_only:
        model = YOLO(args.model)
        model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, device=args.device,
                    seed=args.seed, deterministic=True, patience=25, mosaic=1.0, close_mosaic=10,
                    project=str(ENGINE / "runs"), name="flower_yolo11", exist_ok=True)
        weights = Path(model.trainer.best)
    else:
        weights = Path(args.weights)
    model = YOLO(str(weights))
    val = model.val(data=args.data, split="val", imgsz=args.imgsz, device=args.device)
    test = model.val(data=args.data, split="test", imgsz=args.imgsz, device=args.device)  # evaluated once
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "weights": str(weights), "imgsz": args.imgsz,
        "val": {"mAP50": float(val.box.map50), "mAP50_95": float(val.box.map)},
        "test": {"mAP50": float(test.box.map50), "mAP50_95": float(test.box.map), "precision": float(test.box.mp),
                 "recall": float(test.box.mr)},
        "speed_ms": test.speed,
    }
    (ENGINE / "reports").mkdir(exist_ok=True)
    (ENGINE / "reports" / "yolo11_evaluation.json").write_text(json.dumps(report, indent=2))
    onnx = Path(model.export(format="onnx", imgsz=min(args.imgsz, 1280), simplify=True, dynamic=False))
    shutil.copy2(onnx, ENGINE / "models" / "flower_yolo11n.onnx")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
