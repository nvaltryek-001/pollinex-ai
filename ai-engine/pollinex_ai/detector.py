"""Flower detection back-ends.

1. ``PixelFlowerDetector`` – the model trained in this repository on CPU
   (pixel classifier -> probability map -> watershed instances -> boxes).
2. ``OnnxYoloDetector`` – optional; loads a YOLO11 model exported to ONNX by
   ``ai-engine/training/train_yolo11.py``. Used automatically when its file exists.

Both return the same ``Detection`` objects so the rest of the platform does not care which one ran.
"""
from __future__ import annotations

import json

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from scipy import ndimage as ndi

from .features import FEATURE_VERSION, pixel_features

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


@dataclass
class Detection:
    box: list[float]          # [x1, y1, x2, y2] in ORIGINAL image pixels
    score: float              # model confidence in [0, 1]
    area_px: float
    center: list[float]       # [cx, cy] image-space
    label: str = "flower"
    low_confidence: bool = False
    mask_rle: dict | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("mask_rle", None)
        return d


@dataclass
class DetectionResult:
    detections: list[Detection]
    backend: str
    model_version: str
    latency_ms: float
    image_size: tuple[int, int]
    prob_map: np.ndarray | None = None    # (h, w) at working resolution, for overlays/heuristics
    work_scale: float = 1.0
    warnings: list[str] = field(default_factory=list)


def _resize_long(img: np.ndarray, side: int) -> tuple[np.ndarray, float]:
    h, w = img.shape[:2]
    s = side / max(h, w)
    if abs(s - 1.0) < 1e-6:
        return img, 1.0
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR
    return cv2.resize(img, (int(round(w * s)), int(round(h * s))), interpolation=interp), s


def instances_from_prob(prob: np.ndarray, threshold: float, min_area: int, peak_distance: int,
                        max_area_frac: float = 0.25) -> list[tuple[list[float], float, float]]:
    """Split a flower-probability map into instances with distance-transform watershed.

    Returns (box[x1,y1,x2,y2], score, area) tuples at the prob-map resolution.
    """
    fg = prob >= threshold
    fg = ndi.binary_opening(fg, structure=np.ones((3, 3)))
    fg = ndi.binary_fill_holes(fg)
    if not fg.any():
        return []
    h, w = prob.shape
    if peak_distance <= 0:  # plain connected components (clusters stay together)
        comp, _ = ndi.label(fg, structure=np.ones((3, 3)))
        out = []
        for lab_id, sl in enumerate(ndi.find_objects(comp), start=1):
            if sl is None:
                continue
            region = comp[sl] == lab_id
            area = float(region.sum())
            if area < min_area or area > max_area_frac * h * w:
                continue
            ys, xs = sl
            out.append(([float(xs.start), float(ys.start), float(xs.stop), float(ys.stop)],
                        float(prob[sl][region].mean()), area))
        return out
    dist = ndi.distance_transform_edt(fg)
    # markers = local maxima of the distance map with a minimum separation
    size = max(3, 2 * peak_distance + 1)
    maxf = ndi.maximum_filter(dist, size=size)
    peaks = (dist == maxf) & (dist >= max(1.0, peak_distance * 0.5)) & fg
    markers, n_markers = ndi.label(peaks)
    comp, n_comp = ndi.label(fg)
    if n_markers == 0:
        markers = comp
    else:
        # components without any peak still need a marker
        has_marker = np.zeros(n_comp + 1, dtype=bool)
        has_marker[np.unique(comp[markers > 0])] = True
        orphan = (~has_marker[comp]) & fg
        if orphan.any():
            o_lab, _ = ndi.label(orphan)
            markers = np.where(o_lab > 0, o_lab + markers.max(), markers)
    # watershed on -dist restricted to fg (OpenCV implementation; needs 3-channel image)
    ws_markers = markers.astype(np.int32).copy()
    ws_markers[~fg] = 0
    bg_label = ws_markers.max() + 1
    ws_markers[~ndi.binary_dilation(fg, iterations=2)] = bg_label
    d8 = (255 * (1 - dist / max(dist.max(), 1e-6))).astype(np.uint8)
    labels = cv2.watershed(cv2.cvtColor(d8, cv2.COLOR_GRAY2BGR), ws_markers)
    labels[(labels == bg_label) | (labels < 0) | ~fg] = 0
    out = []
    h, w = prob.shape
    objs = ndi.find_objects(labels)
    for lab_id, sl in enumerate(objs, start=1):
        if sl is None:
            continue
        region = labels[sl] == lab_id
        area = float(region.sum())
        if area < min_area or area > max_area_frac * h * w:
            continue
        score = float(prob[sl][region].mean())
        ys, xs = sl
        out.append(([float(xs.start), float(ys.start), float(xs.stop), float(ys.stop)], score, area))
    return out


class PixelFlowerDetector:
    backend = "pixel-hgb-watershed"

    def __init__(self, model_path: str | Path | None = None):
        import joblib  # lazy: only needed when the model is used

        path = Path(model_path) if model_path else MODELS_DIR / "flower_pixel_hgb.joblib"
        if not path.exists():
            raise FileNotFoundError(f"detector model not found: {path}. Run ai-engine/training/train_detector.py")
        bundle: dict[str, Any] = joblib.load(path)
        if bundle.get("feature_version") != FEATURE_VERSION:
            raise RuntimeError("model was trained with a different feature version; retrain it")
        self.model = bundle["model"]
        self.params: dict = bundle["params"]
        self.version: str = bundle.get("version", "unknown")
        self.meta = {k: v for k, v in bundle.items() if k not in ("model",)}

    def probability_map(self, rgb: np.ndarray, side: int | None = None, stride: int | None = None) -> tuple[np.ndarray, float]:
        """Flower probability at working resolution.

        ``stride`` > 1 classifies a sub-sampled pixel grid and bilinearly upsamples the result
        (features are still computed at full working resolution). Chosen on the VALIDATION split
        as the speed/accuracy trade-off - see ai-engine/reports/detector_inference_tradeoff.json.
        """
        side = int(side or self.params["work_side"])
        stride = int(stride or self.params.get("stride", 1))
        work, s = _resize_long(rgb, side)
        feats = pixel_features(work)
        h, w, f = feats.shape
        sub = feats[::stride, ::stride] if stride > 1 else feats
        sh, sw_ = sub.shape[:2]
        p = self.model.predict_proba(sub.reshape(-1, f))[:, 1].reshape(sh, sw_).astype(np.float32)
        if stride > 1:
            p = cv2.resize(p, (w, h), interpolation=cv2.INTER_LINEAR)
        return p, s

    def detect(self, rgb: np.ndarray, conf_threshold: float | None = None, fast: bool = False) -> DetectionResult:
        """``fast=True`` (live scanning) runs at ``fast_side`` resolution; min_area is rescaled accordingly."""
        t0 = time.perf_counter()
        p = self.params
        side = int(p.get("fast_side", 640) if fast else p["work_side"])
        prob, s = self.probability_map(rgb, side=side)
        area_scale = (side / float(p["work_side"])) ** 2
        inst = instances_from_prob(prob, p["threshold"], max(2, int(round(p["min_area"] * area_scale))),
                                   int(round(p["peak_distance"] * side / float(p["work_side"]))))
        low = conf_threshold if conf_threshold is not None else p.get("low_conf", 0.6)
        dets = []
        for (x1, y1, x2, y2), score, area in inst:
            box = [x1 / s, y1 / s, x2 / s, y2 / s]
            dets.append(Detection(box=[round(v, 1) for v in box], score=round(score, 4), area_px=area / (s * s),
                                  center=[round((box[0] + box[2]) / 2, 1), round((box[1] + box[3]) / 2, 1)],
                                  low_confidence=score < low))
        dets.sort(key=lambda d: -d.score)
        warnings = []
        if dets and sum(d.low_confidence for d in dets) / len(dets) > 0.5:
            warnings.append("More than half of the detections are low-confidence; image may be outside the training domain.")
        return DetectionResult(dets, self.backend, self.version, (time.perf_counter() - t0) * 1000,
                               (rgb.shape[1], rgb.shape[0]), prob, s, warnings)


class OnnxYoloDetector:
    """YOLO11 detector exported to ONNX (output: 1 x (4+nc) x N); see training/train_yolo11.py + yolo_deploy_rule.py."""

    backend = "yolo11-onnx"

    def __init__(self, onnx_path: str | Path, imgsz: int = 640, names: list[str] | None = None):
        import onnxruntime as ort

        self.session = ort.InferenceSession(str(onnx_path), providers=ort.get_available_providers())
        self.input_name = self.session.get_inputs()[0].name
        self.imgsz = imgsz
        self.names = names or ["flower"]
        self.version = Path(onnx_path).stem

    def detect(self, rgb: np.ndarray, conf_threshold: float = 0.25, iou: float = 0.5, fast: bool = False) -> DetectionResult:
        t0 = time.perf_counter()
        h, w = rgb.shape[:2]
        r = self.imgsz / max(h, w)
        nh, nw = int(round(h * r)), int(round(w * r))
        canvas = np.full((self.imgsz, self.imgsz, 3), 114, np.uint8)
        canvas[:nh, :nw] = cv2.resize(rgb, (nw, nh))
        x = canvas.astype(np.float32).transpose(2, 0, 1)[None] / 255.0
        out = self.session.run(None, {self.input_name: x})[0][0]  # (4+nc, N)
        boxes_xywh = out[:4].T
        cls_scores = out[4:].T
        cls = cls_scores.argmax(1)
        conf = cls_scores.max(1)
        keep = conf >= min(conf_threshold, 0.05)
        boxes_xywh, conf, cls = boxes_xywh[keep], conf[keep], cls[keep]
        xyxy = np.stack([boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2, boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2,
                         boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2, boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2], 1) / r
        idx = cv2.dnn.NMSBoxes([[float(b[0]), float(b[1]), float(b[2] - b[0]), float(b[3] - b[1])] for b in xyxy],
                               conf.tolist(), 0.0, iou)
        idx = np.array(idx).reshape(-1)
        dets = []
        for i in idx:
            b = np.clip(xyxy[i], 0, [w, h, w, h]).tolist()
            dets.append(Detection(box=[round(v, 1) for v in b], score=float(conf[i]),
                                  area_px=float((b[2] - b[0]) * (b[3] - b[1])),
                                  center=[(b[0] + b[2]) / 2, (b[1] + b[3]) / 2], label=self.names[int(cls[i])],
                                  low_confidence=float(conf[i]) < conf_threshold))
        return DetectionResult(dets, self.backend, self.version, (time.perf_counter() - t0) * 1000, (w, h))


def load_default_detector():
    onnx = MODELS_DIR / "flower_yolo11n.onnx"
    if onnx.exists():
        side = onnx.with_suffix(".json")
        cfg = json.loads(side.read_text()) if side.exists() else {}
        return OnnxYoloDetector(onnx, imgsz=cfg.get("imgsz", 640), names=cfg.get("names"))
    return PixelFlowerDetector()
