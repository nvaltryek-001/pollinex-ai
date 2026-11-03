"""Visible-anomaly indicators for a flower crop (HEURISTIC, no disease diagnosis).

Reports measurable visual signals - browning, dark spots, discolouration, outline irregularity
(a wilting / petal-damage proxy) - with the values that triggered them. It never names a disease:
the same symptoms have many causes (frost, sunscald, pests, pathogens, age).
"""
from __future__ import annotations

import cv2
import numpy as np

from .regions import colour_classes, crop_flower_mask, fractions

THRESHOLDS = {"browning": 0.12, "dark_spots": 3, "discoloration": 0.25, "irregular_outline": 0.70,
              "wilting_low_saturation": 0.18, "wilting_brown": 0.06}
# Each indicator is mapped to one of the four reported categories (none of them is validated against labels yet).
CATEGORY = {"browning": "discoloration", "discoloration": "discoloration", "visible_spots": "visible_abnormality",
            "irregular_outline_possible_damage_or_wilting": "petal_damage",
            "wilting_or_senescence_possible": "wilting"}


def analyze_health(crop: np.ndarray, prob_crop: np.ndarray | None = None) -> dict:
    mask = crop_flower_mask(crop, prob_crop)
    if mask.sum() < 20:
        return {"indicators": [], "status": "insufficient_region", "method": "heuristic"}
    col = fractions(mask, colour_classes(crop))
    L = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32)
    med = np.median(L[mask])
    # dark spots: small blobs much darker than the petal median, inside the flower mask
    dark = ((L < med - 45) & mask).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(dark)
    spots = [s for s in stats[1:] if 3 <= s[cv2.CC_STAT_AREA] <= 0.05 * mask.sum()]
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV).astype(np.float32)
    hue = hsv[..., 0][mask] * 2 * np.pi / 180
    sat = hsv[..., 1][mask] / 255
    vec = np.stack([np.cos(hue) * sat, np.sin(hue) * sat], 1)
    disc = float((np.linalg.norm(vec - np.median(vec, 0), axis=1) > 0.35).mean())
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnts, key=cv2.contourArea)
    solidity = cv2.contourArea(c) / max(cv2.contourArea(cv2.convexHull(c)), 1)
    mean_sat = float(sat.mean())
    ind = []
    if col["brown"] > THRESHOLDS["browning"]:
        ind.append({"type": "browning", "value": round(col["brown"], 3), "threshold": THRESHOLDS["browning"]})
    if len(spots) >= THRESHOLDS["dark_spots"]:
        ind.append({"type": "visible_spots", "value": len(spots), "threshold": THRESHOLDS["dark_spots"]})
    if disc > THRESHOLDS["discoloration"]:
        ind.append({"type": "discoloration", "value": round(disc, 3), "threshold": THRESHOLDS["discoloration"]})
    if solidity < THRESHOLDS["irregular_outline"]:
        ind.append({"type": "irregular_outline_possible_damage_or_wilting", "value": round(float(solidity), 3),
                    "threshold": THRESHOLDS["irregular_outline"]})
    if mean_sat < THRESHOLDS["wilting_low_saturation"] and col["brown"] > THRESHOLDS["wilting_brown"]:
        ind.append({"type": "wilting_or_senescence_possible", "value": round(mean_sat, 3),
                    "threshold": THRESHOLDS["wilting_low_saturation"]})
    for i in ind:
        i["category"] = CATEGORY[i["type"]]
    return {
        "indicators": ind, "categories": sorted({i["category"] for i in ind}), "status": "anomalies_visible" if ind else "no_visible_anomaly_detected",
        "measurements": {"brown_fraction": round(col["brown"], 4), "dark_spot_count": len(spots),
                         "discoloration_fraction": round(disc, 4), "outline_solidity": round(float(solidity), 4), "mean_saturation": round(mean_sat, 4)},
        "method": "heuristic",
        "note": "Observable visual indicators only - not a disease diagnosis. Confirm with an agronomist or plant pathologist.",
    }
