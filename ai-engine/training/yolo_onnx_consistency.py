#!/usr/bin/env python3
"""Check that the exported ONNX model + Pollinex pre/post-processing reproduce Ultralytics PyTorch predictions.

Runs best.pt (Ultralytics predict) and the exported ONNX (pollinex_ai.detector.OnnxYoloDetector) on the first 30 test
images of each committed box set at the same image size and confidence 0.25, then greedily matches boxes (IoU >= 0.8).
Writes ai-engine/reports/yolo11_onnx_consistency.json: matched fraction both ways, mean |score difference|, mean IoU.
Differences are expected to be small (Ultralytics letterboxes to a stride-aligned rectangle; Pollinex pads to a square).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "training"))
from evaluate_detector_on import image_list  # noqa: E402
from pollinex_ai.detector import OnnxYoloDetector  # noqa: E402
from pollinex_ai.metrics import iou_matrix  # noqa: E402

PROC = ENGINE.parent / "datasets" / "processed"


def main():
    from ultralytics import YOLO

    exp = ENGINE / "runs" / "export"
    cfg = json.loads((exp / "flower_yolo11n.json").read_text())
    pt = YOLO(str(ENGINE / "runs" / "flower_yolo11" / "weights" / "best.pt"))
    onnx = OnnxYoloDetector(exp / "flower_yolo11n.onnx", imgsz=cfg["imgsz"])
    n_pt = n_onnx = matched = 0
    sdiff, ious = [], []
    for root in (PROC / "usda_fruit_flower", PROC / "tf_flower_detection_sunflower"):
        for im in image_list(root, "test")[:30]:
            rgb = np.array(Image.open(im).convert("RGB"))
            r = pt.predict(rgb[..., ::-1].copy(), imgsz=cfg["imgsz"], conf=0.25, iou=0.5, verbose=False)[0]
            a, sa = r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()
            res = onnx.detect(rgb, conf_threshold=0.25)
            b = np.array([d.box for d in res.detections if not d.low_confidence], np.float32).reshape(-1, 4)
            sb = np.array([d.score for d in res.detections if not d.low_confidence])
            n_pt, n_onnx = n_pt + len(a), n_onnx + len(b)
            if len(a) and len(b):
                m = iou_matrix(a, b)
                used = np.zeros(len(b), bool)
                for i in np.argsort(-sa):
                    row = np.where(used, -1, m[i])
                    j = int(row.argmax())
                    if row[j] >= 0.8:
                        used[j] = True
                        matched += 1
                        sdiff.append(abs(float(sa[i]) - float(sb[j])))
                        ious.append(float(row[j]))
    out = {"images": "first 30 test images of each set", "imgsz": cfg["imgsz"], "pytorch_boxes": n_pt, "onnx_boxes": n_onnx,
           "matched_iou>=0.8": matched, "matched_fraction_of_pytorch": matched / max(n_pt, 1),
           "matched_fraction_of_onnx": matched / max(n_onnx, 1),
           "mean_abs_score_diff": float(np.mean(sdiff)) if sdiff else None, "mean_iou_of_matches": float(np.mean(ious)) if ious else None}
    (ENGINE / "reports" / "yolo11_onnx_consistency.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
