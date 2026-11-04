"""End-to-end image analysis used by the API, CLI and tests.

Every field carries its provenance:
  detection  -> trained model (``method: trained_model``) or close-up fallback (``method: closeup_fallback``)
  species    -> gallery kNN (``trained_reference_gallery``) or user-declared (``user_declared``)
  stage / centre / health -> ``heuristic``
  readiness  -> ``rule_engine``
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from .detector import MODELS_DIR, Detection, load_default_detector
from .health import analyze_health
from .maturity import estimate_stage
from .pose import estimate_pose
from .readiness import estimate_readiness
from .species import UNKNOWN, SpeciesGallery, crop_box
from .structure import apply_structure_model, load_structure_model
from .structure import analyze_centre

GALLERY_PATH = MODELS_DIR / "species_gallery"


class Analyzer:
    def __init__(self, detector=None, gallery: SpeciesGallery | None = None, gallery_path: str | Path | None = None):
        self.detector = detector or load_default_detector()
        if gallery is not None:
            self.gallery = gallery
        else:
            gp = Path(gallery_path) if gallery_path else GALLERY_PATH
            self.gallery = SpeciesGallery.load(gp) if gp.with_suffix(".json").exists() else SpeciesGallery()
        self.structure_model = load_structure_model()  # None until a structure model trained on real annotations exists
        # crop/scene vote blending selected on validation for the shipped gallery only (species_context_rule.py)
        ctx = MODELS_DIR / "species_context.json"
        self.species_context = (json.loads(ctx.read_text()) if gallery is None and gallery_path is None and ctx.exists() else {})

    def model_info(self) -> dict:
        return {"detector_backend": self.detector.backend, "detector_version": self.detector.version,
                "gallery_species": self.gallery.counts(), "gallery_threshold": self.gallery.threshold,
                "gallery_version": self.gallery.meta.get("gallery_version") or self.gallery.meta.get("embed_version"),
                "species_context": {k: self.species_context[k] for k in ("crop_weight", "abstain_share") if k in self.species_context} or None,
                "structure_model": self.structure_model.version if self.structure_model is not None else None}

    def _prob_crop(self, res, box):
        if res.prob_map is None:
            return None
        s = res.work_scale
        x1, y1, x2, y2 = [int(round(v * s)) for v in box]
        return res.prob_map[max(0, y1):max(y2, y1 + 1), max(0, x1):max(x2, x1 + 1)]

    def analyze(self, rgb: np.ndarray, mode: str = "auto", species_hint: str | None = None, env: dict | None = None,
                max_flowers: int = 25, detail: bool = True, fast: bool = False) -> dict[str, Any]:
        if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
            raise ValueError("expected an RGB uint8 image")
        if min(rgb.shape[:2]) < 32:
            raise ValueError("image too small (min side 32 px)")
        t0 = time.perf_counter()
        H, W = rgb.shape[:2]
        warnings: list[str] = []
        res = None
        dets: list[Detection] = []
        det_method = "trained_model"
        if mode in ("auto", "scene"):
            res = self.detector.detect(rgb, fast=fast)
            dets = res.detections
            warnings += res.warnings
        confident = [d for d in dets if not d.low_confidence]
        if mode == "closeup" or (mode == "auto" and not confident):
            if mode == "auto":
                warnings.append("No confident detections from the flower detector (trained on apple, peach, pear and sunflower boxes); analysed the image as a "
                                "single close-up flower (close-up fallback - not a model detection).")
            mx, my = 0.1 * W, 0.1 * H
            box = [mx, my, W - mx, H - my]
            dets = [Detection(box=box, score=0.0, area_px=(W - 2 * mx) * (H - 2 * my), center=[W / 2, H / 2])]
            det_method = "closeup_fallback"
            res_for_crop = None
        else:
            res_for_crop = res
        flowers = []
        scene_vec = None
        ctx_w = self.species_context.get("crop_weight", 1.0)
        if det_method == "trained_model" and not species_hint and ctx_w < 1.0:
            mx, my = int(0.1 * W), int(0.1 * H)
            scene_vec = self.gallery.embed_fn(rgb[my:H - my, mx:W - mx])  # same centre-80 % view as close-up mode
        for i, d in enumerate(dets[:max_flowers]):
            # close-up: exactly the centre-80 % crop the gallery was evaluated on; detections: 10 % context padding
            crop = crop_box(rgb, d.box, pad=0.0 if det_method == "closeup_fallback" else 0.1)
            pc = self._prob_crop(res_for_crop, d.box) if res_for_crop is not None else None
            if species_hint:
                sp = {"species": species_hint, "confidence": 1.0, "method": "user_declared", "candidates": []}
            else:
                if scene_vec is not None:
                    sp = {**self.gallery.predict_fused(self.gallery.embed_fn(crop), scene_vec, ctx_w), "method": "trained_reference_gallery"}
                else:
                    sp = {**self.gallery.predict(crop), "method": "trained_reference_gallery"}
                status = self.gallery.meta.get("species_status", {})
                if sp["species"] != UNKNOWN:
                    sp["support"] = status.get(sp["species"], "not_evaluated")
            item: dict[str, Any] = {"id": i, "detection": {**d.to_dict(), "method": det_method}, "species": sp}
            if detail:
                stage = estimate_stage(crop, pc)
                centre = analyze_centre(crop, pc)
                if self.structure_model is not None:
                    centre = apply_structure_model(centre, crop, self.structure_model)
                health = analyze_health(crop, pc)
                item.update({
                    "stage": stage, "structure": centre, "health": health,
                    "pose": estimate_pose(crop, d.box, (W, H), pc),
                    "readiness": estimate_readiness(sp["species"], stage, centre, health, env,
                                                    detection_score=d.score if det_method == "trained_model" else 0.6,
                                                    species_confidence=sp.get("confidence", 0.0) or 0.0),
                })
            flowers.append(item)
        if len(dets) > max_flowers:
            warnings.append(f"{len(dets)} flowers detected; detailed analysis limited to the top {max_flowers} by confidence.")
        species_counts: dict[str, int] = {}
        for f in flowers:
            species_counts[f["species"]["species"]] = species_counts.get(f["species"]["species"], 0) + 1
        return {
            "image_size": [W, H], "mode": mode, "detection_method": det_method,
            "flower_count": len(dets) if det_method == "trained_model" else 1,
            "low_confidence_count": sum(d.low_confidence for d in dets) if det_method == "trained_model" else None,
            "species_counts": species_counts, "flowers": flowers, "warnings": warnings,
            "model": self.model_info(), "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "unknown_species_present": UNKNOWN in species_counts,
        }
