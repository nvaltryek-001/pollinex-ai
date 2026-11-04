#!/usr/bin/env python3
"""YOLO11 fine-tuning recipe (Ultralytics, AGPL-3.0) -> ONNX for the backend.

Runs on CPU (GitHub Actions: .github/workflows/yolo.yml) or GPU (Colab: notebooks/train_yolo11_colab.ipynb).

    pip install -r ai-engine/requirements-train.txt
    python ai-engine/training/train_yolo11.py --combined --imgsz 800 --time 4 --device cpu   # USDA + sunflower
    python ai-engine/training/train_yolo11.py --data datasets/processed/usda_fruit_flower/data.yaml
    python ai-engine/training/train_yolo11.py --data ... --evaluate-only --weights runs/.../best.pt

--combined builds a one-class "flower" dataset from every committed box-annotated set (USDA apple/peach/pear and the
TF Flower Detection sunflower subset), keeping each source's own train/val/test split, so no test image is ever trained on.

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
    ap.add_argument("--data", default=None, help="YOLO data.yaml (train/val/test)")
    ap.add_argument("--combined", action="store_true", help="USDA + sunflower one-class dataset (own splits)")
    ap.add_argument("--time", type=float, default=None, help="max training hours (overrides epochs)")
    ap.add_argument("--model", default="yolo11n.pt")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=1280, help="flowers are small; keep resolution high")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default=None, help="'cpu', '0', ...")
    ap.add_argument("--weights", default=None)
    ap.add_argument("--evaluate-only", action="store_true")
    ap.add_argument("--seed", type=int, default=20261102)
    ap.add_argument("--report-name", default="yolo11_evaluation", help="reports/<name>.json (+ <name>_training_curve.csv)")
    args = ap.parse_args()

    from ultralytics import YOLO  # imported here so the rest of the repo never needs torch

    if args.combined:
        args.data = str(write_combined_yaml())
    if not args.data:
        ap.error("--data or --combined is required")

    if not args.evaluate_only:
        model = YOLO(args.model)
        model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, device=args.device,
                    seed=args.seed, deterministic=True, patience=15, mosaic=1.0, close_mosaic=5, time=args.time,
                    workers=2, plots=False,
                    project=str(ENGINE / "runs"), name="flower_yolo11", exist_ok=True)
        weights = Path(model.trainer.best)
    else:
        weights = Path(args.weights)
    model = YOLO(str(weights))
    val = model.val(data=args.data, split="val", imgsz=args.imgsz, device=args.device)
    test = model.val(data=args.data, split="test", imgsz=args.imgsz, device=args.device)  # evaluated once
    report = {
        "data": args.data if not args.combined else "combined: usda_fruit_flower + tf_flower_detection_sunflower",
        "epochs_completed": _epochs_done(weights),
        "generated_at": datetime.now(timezone.utc).isoformat(), "weights": str(weights), "imgsz": args.imgsz,
        "val": {"mAP50": float(val.box.map50), "mAP50_95": float(val.box.map)},
        "test": {"mAP50": float(test.box.map50), "mAP50_95": float(test.box.map), "precision": float(test.box.mp),
                 "recall": float(test.box.mr)},
        "speed_ms": test.speed,
    }
    (ENGINE / "reports").mkdir(exist_ok=True)
    (ENGINE / "reports" / f"{args.report_name}.json").write_text(json.dumps(report, indent=2))
    onnx = Path(model.export(format="onnx", imgsz=args.imgsz, simplify=True, dynamic=False))
    out_dir = ENGINE / "runs" / "export"
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(onnx, out_dir / "flower_yolo11n.onnx")  # candidate; promoted to models/ only by the deploy rule
    (out_dir / "flower_yolo11n.json").write_text(json.dumps({"imgsz": args.imgsz, "names": ["flower"],
                                                             "trained_at": report["generated_at"]}))
    res_csv = weights.parent.parent / "results.csv"
    if res_csv.exists():
        shutil.copy2(res_csv, ENGINE / "reports" / f"{args.report_name.replace('_evaluation', '')}_training_curve.csv")
    print(json.dumps(report, indent=2))


def _epochs_done(weights: Path) -> int | None:
    res_csv = weights.parent.parent / "results.csv"
    return sum(1 for _ in res_csv.open()) - 1 if res_csv.exists() else None


def write_combined_yaml() -> Path:
    root = ENGINE.parent / "datasets" / "processed"
    usda, sun = root / "usda_fruit_flower", root / "tf_flower_detection_sunflower"
    out = ENGINE / "runs" / "combined_flower.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# generated by train_yolo11.py --combined (one class, each source keeps its own split)"]
    for split in ("train", "val", "test"):
        lines.append(f"{split}: [{usda / (split + '.txt')}, {sun / split / 'images'}]")
    lines += ["names:", "  0: flower"]
    out.write_text("\n".join(lines) + "\n")
    return out


if __name__ == "__main__":
    main()
