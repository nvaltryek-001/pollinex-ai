"""Flower developmental-stage estimate (HEURISTIC).

No openly licensed stage-labelled dataset was available for the target crops (see
research/research_gaps.md, Gap 3). This module therefore scores five visible stages from interpretable
shape and colour cues. It is labelled ``method: heuristic`` everywhere it is shown, and it says
nothing about pollen viability or stigma receptivity.

A trained replacement can be produced with ai-engine/training/train_stage_classifier.py once
stage annotations exist (annotation schema in datasets/annotation/).
"""
from __future__ import annotations

import cv2
import numpy as np

from .regions import colour_classes, crop_flower_mask, fractions

STAGES = ["bud", "early_bloom", "partially_open", "fully_open", "senescent"]


def _shape_cues(mask: np.ndarray) -> dict:
    m = mask.astype(np.uint8)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return {"fill": 0.0, "solidity": 0.0, "elongation": 1.0, "radial_cv": 1.0}
    c = max(cnts, key=cv2.contourArea)
    area = cv2.contourArea(c)
    hull = cv2.contourArea(cv2.convexHull(c)) or 1.0
    (cx, cy), radius = cv2.minEnclosingCircle(c)
    fill = area / max(np.pi * radius * radius, 1.0)
    elong = 1.0
    if len(c) >= 5:
        (_, _), (ma, MA), _ = cv2.fitEllipse(c)
        elong = max(ma, MA) / max(min(ma, MA), 1e-6)
    pts = c.reshape(-1, 2).astype(np.float32)
    d = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
    radial_cv = float(d.std() / max(d.mean(), 1e-6))  # petal lobes -> higher variation
    return {"fill": float(fill), "solidity": float(area / hull), "elongation": float(elong), "radial_cv": radial_cv}


def estimate_stage(crop: np.ndarray, prob_crop: np.ndarray | None = None) -> dict:
    mask = crop_flower_mask(crop, prob_crop)
    shape = _shape_cues(mask)
    col = fractions(mask, colour_classes(crop))
    petal = col["white"] + max(0.0, 1 - col["green"] - col["brown"] - col["dark"] - col["white"]) * 0.5
    s = {
        # compact, elongated, green-dominant
        "bud": 1.6 * col["green"] + 0.8 * min(shape["elongation"] - 1, 1.5) + 0.8 * shape["solidity"] - 0.8 * shape["radial_cv"],
        # mostly closed but petal colour showing
        "early_bloom": 0.9 * shape["solidity"] + 0.6 * petal + 0.4 * min(shape["elongation"] - 1, 1.0) - 0.6 * col["brown"],
        # petals separating: medium fill, some lobing
        "partially_open": 0.8 * petal + 1.2 * min(shape["radial_cv"], 0.35) / 0.35 * 0.5 + 0.4 * (1 - abs(shape["fill"] - 0.55) * 2),
        # wide, round, lobed corolla, little green or brown
        "fully_open": 1.2 * petal + 0.8 * shape["fill"] + 0.6 * min(shape["radial_cv"], 0.3) / 0.3 - 1.0 * col["green"] - 1.2 * col["brown"],
        # browning, dark tissue, ragged outline
        "senescent": 2.4 * col["brown"] + 1.2 * col["dark"] + 0.6 * (1 - shape["solidity"]) - 0.6 * col["white"],
    }
    v = np.array([s[k] for k in STAGES])
    p = np.exp((v - v.max()) * 3.0)
    p /= p.sum()
    best = int(np.argmax(p))
    margin = float(np.sort(p)[-1] - np.sort(p)[-2])
    return {
        "stage": STAGES[best], "score": round(float(p[best]), 4),
        "distribution": {k: round(float(x), 4) for k, x in zip(STAGES, p)},
        "uncertain": margin < 0.15,
        "cues": {**{k: round(v, 4) for k, v in shape.items()}, **{f"frac_{k}": round(v, 4) for k, v in col.items()}},
        "method": "heuristic", "validated": False,
        "note": "Visual stage heuristic from shape/colour cues; not trained on stage labels and not a measure of pollen viability.",
    }
