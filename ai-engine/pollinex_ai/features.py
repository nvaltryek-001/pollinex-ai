"""Pixel feature extraction for the CPU flower segmenter.

An ilastik-style feature stack: colour channels in several spaces, smoothed at multiple scales,
plus edge / blob / texture responses. Everything is OpenCV/numpy so it runs on any laptop CPU.
"""
from __future__ import annotations

import cv2
import numpy as np

SIGMAS = (1.0, 2.0, 4.0)
FEATURE_VERSION = "pfx-v1"


def _gauss(x: np.ndarray, s: float) -> np.ndarray:
    return cv2.GaussianBlur(x, (0, 0), s)


def pixel_features(rgb: np.ndarray) -> np.ndarray:
    """Return an (H, W, F) float32 feature stack for an RGB uint8 image."""
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("expected an RGB uint8 image of shape (H, W, 3)")
    f32 = rgb.astype(np.float32) / 255.0
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    hue = hsv[..., 0] * (2 * np.pi / 180.0)
    sat = hsv[..., 1] / 255.0
    val = hsv[..., 2] / 255.0
    gray = lab[..., 0]
    # whiteness: bright and unsaturated (apple/pear/peach blossoms; many other petals)
    white = val * (1.0 - sat)
    # excess-green index is a classic vegetation separator
    exg = 2 * f32[..., 1] - f32[..., 0] - f32[..., 2]
    base = [f32[..., 0], f32[..., 1], f32[..., 2], lab[..., 1], lab[..., 2], gray,
            np.cos(hue) * sat, np.sin(hue) * sat, sat, val, white, exg]
    feats = list(base)
    for s in SIGMAS:
        g = _gauss(gray, s)
        feats += [_gauss(lab[..., 1], s), _gauss(lab[..., 2], s), g, _gauss(white, s), _gauss(exg, s)]
        gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
        feats.append(np.sqrt(gx * gx + gy * gy))
        feats.append(cv2.Laplacian(g, cv2.CV_32F, ksize=3) * (s * s))  # scale-normalised LoG ~ blobness
        # local contrast (std) of brightness
        m = _gauss(gray, s)
        feats.append(np.sqrt(np.maximum(_gauss(gray * gray, s) - m * m, 0)))
    return np.stack(feats, axis=-1).astype(np.float32)


N_FEATURES = 12 + len(SIGMAS) * 8
