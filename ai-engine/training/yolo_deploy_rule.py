#!/usr/bin/env python3
"""Pre-registered deploy rule for the YOLO11 detector (written BEFORE any YOLO result existed, 2026-11-03).

YOLO11 replaces the pixel detector as the default model only if, on the USDA held-out TEST split and with the same
evaluation code (evaluate_detector_on.py), its mAP@0.5 is >= the pixel detector's. The sunflower test result is reported
either way (the pixel detector cannot detect sunflowers: mAP@0.5 0.001). Writes ai-engine/reports/yolo11_deploy_decision.json
and, if deployed, copies the ONNX model + sidecar into ai-engine/models/ (the backend then loads it automatically).
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
R = ENGINE / "reports"


def m(name):
    p = R / f"detector_on_{name}.json"
    return json.loads(p.read_text())["metrics"] if p.exists() else None


pix, yolo, ysun = m("usda_fruit_flower_pixel"), m("usda_fruit_flower_yolo11"), m("tf_flower_detection_sunflower_yolo11")
psun = m("tf_flower_detection_sunflower")
deploy = bool(pix and yolo and yolo["mAP50"] >= pix["mAP50"])
keys = ("mAP50", "mAP50_95", "precision@0.5", "recall@0.5", "f1@0.5")
pick = lambda d: {k: d.get(k) for k in keys} if d else None  # noqa: E731
decision = {"generated_at": datetime.now(timezone.utc).isoformat(),
            "rule": "deploy YOLO11 iff USDA-test mAP@0.5 (same evaluation code) >= pixel detector's",
            "usda_test": {"pixel": pick(pix), "yolo11": pick(yolo)},
            "sunflower_test": {"pixel": pick(psun), "yolo11": pick(ysun)},
            "deployed": deploy,
            "licence_note": "Ultralytics YOLO11 is AGPL-3.0; the exported model is distributed under AGPL-3.0 terms "
                            "(see ai-engine/models/YOLO11_LICENSE_NOTE.md). Delete the .onnx to fall back to the MIT pixel model."}
if deploy:
    for ext in (".onnx", ".json"):
        shutil.copy2(ENGINE / "runs" / "export" / f"flower_yolo11n{ext}", ENGINE / "models" / f"flower_yolo11n{ext}")
(R / "yolo11_deploy_decision.json").write_text(json.dumps(decision, indent=2))
print(json.dumps(decision, indent=2))
