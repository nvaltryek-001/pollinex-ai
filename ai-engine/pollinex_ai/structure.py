"""Flower centre-region analysis (HEURISTIC) - *not* anther/stigma detection.

We found no openly licensed anther/stigma annotations for the nine target crops that were reachable
for this project, so no reproductive-structure detector is trained. This module only locates the
visually distinct *centre region* of an open flower (where anthers/stigma usually sit) and reports
whether a saturated yellow cluster - a common appearance of dehisced anthers - is visible there.

Outputs are labelled ``method: heuristic`` and ``structure_detection_available: False``.
When a trained structure model (ai-engine/models/structures_yolo.onnx) is installed, the pipeline
reports that model's detections instead.
"""
from __future__ import annotations

import cv2
import numpy as np

from .regions import colour_classes, crop_flower_mask


def analyze_centre(crop: np.ndarray, prob_crop: np.ndarray | None = None) -> dict:
    h, w = crop.shape[:2]
    mask = crop_flower_mask(crop, prob_crop)
    if mask.sum() < 20:
        return {"centre_region": None, "yellow_cluster_visible": False, "method": "heuristic",
                "structure_detection_available": False, "note": "flower region too small to analyse"}
    lab = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB).astype(np.float32)
    petal_ref = np.median(lab[mask], axis=0)
    diff = np.linalg.norm(lab - petal_ref, axis=2)
    ys, xs = np.nonzero(mask)
    cy, cx = ys.mean(), xs.mean()
    r_eq = np.sqrt(mask.sum() / np.pi)
    yy, xx = np.mgrid[:h, :w]
    near_centre = np.hypot(yy - cy, xx - cx) < 0.45 * r_eq
    cand = (diff > np.percentile(diff[mask], 75)) & near_centre & mask
    cand = cv2.morphologyEx(cand.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    centre = None
    if cand.sum() >= 6:
        n, lab_im, stats, cents = cv2.connectedComponentsWithStats(cand.astype(np.uint8))
        j = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        x, y, bw, bh, area = stats[j]
        centre = {"box": [int(x), int(y), int(x + bw), int(y + bh)], "center": [float(cents[j][0]), float(cents[j][1])],
                  "area_fraction_of_flower": round(float(area / mask.sum()), 4),
                  "colour_contrast_dE": round(float(diff[lab_im == j].mean()), 2)}
    yellow = colour_classes(crop)["yellow"] & near_centre & mask
    yellow_frac = float(yellow.sum() / max(near_centre[mask].sum(), 1))
    petal_px = int(mask.sum() - (cand.sum() if centre else 0))
    structures = [
        {"structure": "petals", "status": "heuristic_region", "visible": petal_px > 0,
         "detail": f"flower mask minus centre region ({petal_px} px)"},
        {"structure": "centre_region", "status": "heuristic_region", "visible": centre is not None,
         "detail": "colour-distinct central area where anthers/stigma usually sit"},
        {"structure": "anther", "status": "not_ai_validated", "visible": None,
         "detail": "no trained model; yellow pollen-like cluster reported only as a visual cue"},
        {"structure": "stigma", "status": "not_ai_validated", "visible": None, "detail": "no trained model"},
        {"structure": "stamen", "status": "not_ai_validated", "visible": None, "detail": "no trained model"},
        {"structure": "pistil", "status": "not_ai_validated", "visible": None, "detail": "no trained model"},
    ]
    return {
        "structures": structures,
        "centre_region": centre, "flower_centroid": [round(float(cx), 1), round(float(cy), 1)],
        "yellow_cluster_visible": yellow_frac > 0.08, "yellow_fraction_in_centre": round(yellow_frac, 4),
        "method": "heuristic", "structure_detection_available": False,
        "note": "Centre-region colour analysis only. Anthers, stigma, stamens and pistil are NOT individually detected.",
    }
