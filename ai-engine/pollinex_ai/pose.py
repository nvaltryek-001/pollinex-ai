"""Image-space flower pose and simulated approach guidance (inspired by FloPE's centre+facing idea).

All quantities are in IMAGE SPACE (pixels / normalised coordinates). Without camera intrinsics
and depth there is no metric distance or 3-D orientation; the guidance is for the virtual simulator.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

from .regions import crop_flower_mask


def estimate_pose(crop: np.ndarray, box, image_size, prob_crop: np.ndarray | None = None,
                  effector_xy: tuple[float, float] | None = None) -> dict:
    W, H = image_size
    x1, y1, x2, y2 = box
    mask = crop_flower_mask(crop, prob_crop)
    m = mask.astype(np.uint8)
    M = cv2.moments(m)
    if M["m00"] > 0:
        cx, cy = x1 + M["m10"] / M["m00"], y1 + M["m01"] / M["m00"]
        mu20, mu02, mu11 = M["mu20"] / M["m00"], M["mu02"] / M["m00"], M["mu11"] / M["m00"]
        common = math.sqrt(max(((mu20 - mu02) / 2) ** 2 + mu11 ** 2, 0))
        l1, l2 = (mu20 + mu02) / 2 + common, (mu20 + mu02) / 2 - common
        angle = 0.5 * math.degrees(math.atan2(2 * mu11, mu20 - mu02))
        facing = math.sqrt(max(l2, 1e-9) / max(l1, 1e-9))  # 1 = round (facing camera), ->0 = edge-on
    else:
        cx, cy, angle, facing = (x1 + x2) / 2, (y1 + y2) / 2, 0.0, 0.0
    ex, ey = effector_xy if effector_xy else (W / 2, H)  # default virtual effector: bottom-centre
    dx, dy = cx - ex, cy - ey
    dist = math.hypot(dx, dy)
    horiz = "right" if dx > 0.02 * W else ("left" if dx < -0.02 * W else "centred")
    vert = "up" if dy < -0.02 * H else ("down" if dy > 0.02 * H else "centred")
    return {
        "center_px": [round(cx, 1), round(cy, 1)],
        "center_norm": [round(cx / W, 4), round(cy / H, 4)],
        "box_px": [round(v, 1) for v in box],
        "major_axis_angle_deg": round(angle, 1),
        "facing_ratio": round(facing, 3),
        "facing_estimate": "facing camera" if facing > 0.75 else ("oblique" if facing > 0.45 else "side-on"),
        "alignment": {"effector_px": [round(ex, 1), round(ey, 1)], "dx_px": round(dx, 1), "dy_px": round(dy, 1),
                      "distance_px": round(dist, 1), "distance_norm": round(dist / math.hypot(W, H), 4),
                      "guidance": f"move {horiz} / {vert} (image space)"},
        "coordinate_space": "image",
        "note": "Image-space estimate only; no depth or camera calibration, so no real-world distance is implied.",
    }
