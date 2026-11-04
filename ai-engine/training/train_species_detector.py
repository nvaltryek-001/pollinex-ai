#!/usr/bin/env python3
"""Species-aware (9-class) YOLO11 flower detector - trains ONLY when enough human-verified boxes exist.

    python datasets/annotation/import_verified_boxes.py --coco reviewed/*.json --include-existing
    python ai-engine/training/train_species_detector.py [--data datasets/processed/species_boxes_verified] [--check-only]

GATE (pre-registered; checked before any training): every class must have at least
    MIN_TRAIN_IMAGES training images, MIN_EVAL_IMAGES validation images and MIN_EVAL_IMAGES test images with verified boxes.
If any class fails, nothing is trained. The report lists the classes that are short, and how many images each one still
needs, with status "pending". The app keeps the deployed single-class `flower` detector plus the species gallery. It never
claims nine-species detection without this model.
Selection and reporting follow yolo_select_rule.py: checkpoint choice on val only, test once; per-class precision, recall,
mAP@0.5 and mAP@0.5:0.95 come from ultralytics' validator on the test split.
Writes ai-engine/reports/species_detector_status.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLASSES = ["apple", "peach", "pear", "sunflower", "hibiscus", "tomato", "strawberry", "brinjal", "chilli"]
MIN_TRAIN_IMAGES, MIN_EVAL_IMAGES = 50, 15
REPORT = ROOT / "ai-engine" / "reports" / "species_detector_status.json"


def class_image_counts(data: Path) -> dict[str, Counter]:
    counts = {c: Counter() for c in CLASSES}
    for split in ("train", "val", "test"):
        for lab in (data / split / "labels").glob("*.txt") if (data / split / "labels").is_dir() else []:
            for cid in {int(r.split()[0]) for r in lab.read_text().splitlines() if r.strip()}:
                counts[CLASSES[cid]][split] += 1
    return counts


def gate(counts: dict[str, Counter]) -> dict:
    short = {}
    for c, n in counts.items():
        need = {"train": max(0, MIN_TRAIN_IMAGES - n["train"]), "val": max(0, MIN_EVAL_IMAGES - n["val"]),
                "test": max(0, MIN_EVAL_IMAGES - n["test"])}
        if any(need.values()):
            short[c] = {"have": dict(n), "still_needed": need}
    return {"passed": not short, "short_classes": short,
            "rule": f"each of {len(CLASSES)} classes >= {MIN_TRAIN_IMAGES} train and >= {MIN_EVAL_IMAGES} val and test images with verified boxes"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "datasets" / "processed" / "species_boxes_verified")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--epochs", type=int, default=150)
    ap.add_argument("--imgsz", type=int, default=960)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()
    counts = class_image_counts(args.data)
    g = gate(counts)
    status = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "data": str(args.data.relative_to(ROOT))
              if args.data.is_relative_to(ROOT) else str(args.data), "classes": CLASSES,
              "verified_images_per_class": {c: dict(n) for c, n in counts.items()}, "gate": g,
              "status": "ready_to_train" if g["passed"] else "pending_verified_annotations", "model": None}
    if not g["passed"] or args.check_only:
        REPORT.write_text(json.dumps(status, indent=2))
        print(json.dumps({"status": status["status"], "short_classes": list(g["short_classes"])}, indent=1))
        return 0
    from ultralytics import YOLO  # training extra (requirements-train.txt); AGPL-3.0

    model = YOLO("yolo11n.pt")
    model.train(data=str(args.data / "data.yaml"), epochs=args.epochs, imgsz=args.imgsz, device=args.device, seed=0,
                project=str(ROOT / "runs"), name="species_detector", exist_ok=True)
    best = ROOT / "runs" / "species_detector" / "weights" / "best.pt"  # ultralytics picks best on VAL fitness
    m = YOLO(str(best))
    res = m.val(data=str(args.data / "data.yaml"), split="test", imgsz=args.imgsz, device=args.device)
    per = {}
    for i, c in enumerate(CLASSES):
        p, r, ap50, ap = res.box.class_result(i)
        per[c] = {"precision": float(p), "recall": float(r), "mAP50": float(ap50), "mAP50_95": float(ap)}
    status.update({"status": "trained_not_deployed", "model": str(best.relative_to(ROOT)), "test_per_class": per,
                   "test_mAP50": float(res.box.map50), "test_mAP50_95": float(res.box.map),
                   "next_step": "export to ONNX and compare with the deployed detector under yolo_deploy_rule.py before deploying"})
    REPORT.write_text(json.dumps(status, indent=2))
    print(json.dumps({k: status[k] for k in ("status", "test_mAP50", "test_mAP50_95")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
