"""Detection and classification metrics (COCO-style AP implemented from first principles).

AP uses 101-point interpolated precision, as in the COCO evaluation protocol.
Boxes are [x1, y1, x2, y2] in pixels.
"""
from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np

IOU_THRESHOLDS = np.round(np.arange(0.5, 0.96, 0.05), 2)


def iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)), dtype=np.float32)
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    ix1 = np.maximum(a[:, None, 0], b[None, :, 0])
    iy1 = np.maximum(a[:, None, 1], b[None, :, 1])
    ix2 = np.minimum(a[:, None, 2], b[None, :, 2])
    iy2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(ix2 - ix1, 0, None) * np.clip(iy2 - iy1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / np.maximum(area_a[:, None] + area_b[None, :] - inter, 1e-9)


def _match(preds: Sequence[dict], gts: Sequence[np.ndarray], thr: float):
    """Greedy COCO matching across a set of images. Returns (scores, tp flags, n_gt)."""
    scores, tps = [], []
    n_gt = 0
    for p, g in zip(preds, gts):
        g = np.asarray(g, dtype=np.float32).reshape(-1, 4)
        n_gt += len(g)
        boxes = np.asarray(p["boxes"], dtype=np.float32).reshape(-1, 4)
        sc = np.asarray(p["scores"], dtype=np.float32)
        order = np.argsort(-sc)
        boxes, sc = boxes[order], sc[order]
        ious = iou_matrix(boxes, g)
        used = np.zeros(len(g), dtype=bool)
        for i in range(len(boxes)):
            tp = 0
            if len(g):
                cand = np.where(~used, ious[i], -1)
                j = int(np.argmax(cand))
                if cand[j] >= thr:
                    used[j] = True
                    tp = 1
            scores.append(sc[i])
            tps.append(tp)
    return np.array(scores), np.array(tps), n_gt


def average_precision(preds: Sequence[dict], gts: Sequence[np.ndarray], thr: float = 0.5) -> dict:
    scores, tps, n_gt = _match(preds, gts, thr)
    if n_gt == 0:
        return {"ap": float("nan"), "precision": float("nan"), "recall": float("nan"), "f1": float("nan")}
    order = np.argsort(-scores, kind="mergesort")
    tp_c = np.cumsum(tps[order])
    fp_c = np.cumsum(1 - tps[order])
    rec = tp_c / n_gt
    prec = tp_c / np.maximum(tp_c + fp_c, 1e-9)
    # precision envelope
    env = np.maximum.accumulate(prec[::-1])[::-1] if len(prec) else prec
    rs = np.linspace(0, 1, 101)
    ap = 0.0
    for r in rs:
        idx = np.searchsorted(rec, r, side="left")
        ap += env[idx] if idx < len(env) else 0.0
    ap /= len(rs)
    final_p = float(prec[-1]) if len(prec) else 0.0
    final_r = float(rec[-1]) if len(rec) else 0.0
    f1 = 2 * final_p * final_r / max(final_p + final_r, 1e-9)
    return {"ap": float(ap), "precision": final_p, "recall": final_r, "f1": float(f1),
            "n_pred": int(len(scores)), "n_gt": int(n_gt), "tp": int(tps.sum()) if len(tps) else 0}


def detection_report(preds: Sequence[dict], gts: Sequence[np.ndarray]) -> dict:
    per_thr = {f"{t:.2f}": average_precision(preds, gts, float(t))["ap"] for t in IOU_THRESHOLDS}
    at50 = average_precision(preds, gts, 0.5)
    return {
        "mAP50": at50["ap"], "mAP50_95": float(np.mean(list(per_thr.values()))),
        "precision@0.5": at50["precision"], "recall@0.5": at50["recall"], "f1@0.5": at50["f1"],
        "n_pred": at50["n_pred"], "n_gt": at50["n_gt"], "tp@0.5": at50["tp"], "ap_per_iou": per_thr,
    }


def count_errors(pred_counts: Iterable[int], gt_counts: Iterable[int]) -> dict:
    p = np.asarray(list(pred_counts), dtype=float)
    g = np.asarray(list(gt_counts), dtype=float)
    return {"count_MAE": float(np.mean(np.abs(p - g))), "count_MAPE": float(np.mean(np.abs(p - g) / np.maximum(g, 1))),
            "count_bias": float(np.mean(p - g))}


def classification_report(y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]) -> dict:
    labels = list(labels)
    idx = {l: i for i, l in enumerate(labels)}
    cm = np.zeros((len(labels), len(labels)), dtype=int)
    for t, p in zip(y_true, y_pred):
        if t in idx and p in idx:
            cm[idx[t], idx[p]] += 1
    per = {}
    for l, i in idx.items():
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        p = tp / max(tp + fp, 1)
        r = tp / max(tp + fn, 1)
        per[l] = {"precision": float(p), "recall": float(r), "f1": float(2 * p * r / max(p + r, 1e-9)), "support": int(cm[i].sum())}
    acc = float(np.trace(cm) / max(cm.sum(), 1))
    macro_f1 = float(np.mean([v["f1"] for v in per.values() if v["support"] > 0])) if per else 0.0
    return {"accuracy": acc, "macro_f1": macro_f1, "per_class": per, "labels": labels, "confusion_matrix": cm.tolist()}
