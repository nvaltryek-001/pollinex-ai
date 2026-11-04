"""Shared helpers: per-crop flower mask and colour-class fractions used by the heuristic modules."""
from __future__ import annotations

import hashlib
from collections import OrderedDict

import cv2
import numpy as np

_MASK_CACHE: OrderedDict = OrderedDict()  # stage/centre/health/pose all need the same mask: compute it once per crop


def crop_flower_mask(crop: np.ndarray, prob_crop: np.ndarray | None = None) -> np.ndarray:
    key = (crop.shape, hashlib.sha1(np.ascontiguousarray(crop).tobytes()).hexdigest(),
           None if prob_crop is None else hashlib.sha1(np.ascontiguousarray(prob_crop).tobytes()).hexdigest())
    if key in _MASK_CACHE:
        _MASK_CACHE.move_to_end(key)
        return _MASK_CACHE[key].copy()
    m = _crop_flower_mask(crop, prob_crop)
    _MASK_CACHE[key] = m
    while len(_MASK_CACHE) > 64:
        _MASK_CACHE.popitem(last=False)
    return m.copy()


def _crop_flower_mask(crop: np.ndarray, prob_crop: np.ndarray | None = None) -> np.ndarray:
    """Binary mask of the flower inside a crop.

    Uses the detector's probability map when available; otherwise falls back to a GrabCut
    initialised with the central 70 % rectangle (works for close-up phone photos).
    """
    h, w = crop.shape[:2]
    if prob_crop is not None and prob_crop.size:
        m = cv2.resize(prob_crop, (w, h), interpolation=cv2.INTER_LINEAR) >= 0.5
        if m.sum() > 0.02 * h * w:
            return m
    if h < 8 or w < 8:
        return np.ones((h, w), bool)
    # 1) background model from the crop border: flower = pixels far (Lab dE) from the border's median colour
    lab = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB).astype(np.float32)
    b = max(1, min(h, w) // 12)
    border = np.concatenate([lab[:b].reshape(-1, 3), lab[-b:].reshape(-1, 3), lab[:, :b].reshape(-1, 3), lab[:, -b:].reshape(-1, 3)])
    d = np.linalg.norm(lab - np.median(border, 0), axis=2)
    m = d > max(25.0, float(np.percentile(np.linalg.norm(border - np.median(border, 0), axis=1), 90)) * 1.5)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab_im, stats, _ = cv2.connectedComponentsWithStats(m)
    if n > 1:
        # keep the component(s) overlapping the crop centre region, else the largest
        cy, cx = h // 2, w // 2
        centre_ids = set(np.unique(lab_im[cy - h // 6: cy + h // 6 + 1, cx - w // 6: cx + w // 6 + 1])) - {0}
        keep = centre_ids or {1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))}
        m2 = np.isin(lab_im, list(keep))
        m2 = cv2.morphologyEx(m2.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
        if 0.08 * h * w <= m2.sum() <= 0.95 * h * w:
            return m2
    # 2) GrabCut initialised with the central rectangle
    mask = np.zeros((h, w), np.uint8)
    rect = (int(w * 0.15), int(h * 0.15), max(1, int(w * 0.7)), max(1, int(h * 0.7)))
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(cv2.cvtColor(crop, cv2.COLOR_RGB2BGR), mask, rect, bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
        m = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    except cv2.error:
        m = np.zeros((h, w), bool)
        m[rect[1]:rect[1] + rect[3], rect[0]:rect[0] + rect[2]] = True
    return m


def colour_classes(crop: np.ndarray) -> dict[str, np.ndarray]:
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV).astype(np.float32)
    H, S, V = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
    return {
        "green": (H > 70) & (H < 170) & (S > 0.25) & (V > 0.15),
        "brown": (((H < 40) | (H > 340)) & (S > 0.3) & (V > 0.12) & (V < 0.55)),
        "yellow": (H >= 40) & (H <= 70) & (S > 0.35) & (V > 0.35),
        "white": (S < 0.18) & (V > 0.7),
        "dark": V < 0.18,
    }


def fractions(mask: np.ndarray, classes: dict[str, np.ndarray]) -> dict[str, float]:
    n = max(int(mask.sum()), 1)
    return {k: float((v & mask).sum() / n) for k, v in classes.items()}
