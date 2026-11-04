"""Open-set species recognition with an expandable reference gallery.

Design
------
* Each flower crop is embedded with a hand-crafted, CPU-cheap descriptor
  (HSV colour histogram + Lab moments + HOG shape + LBP texture), L2-normalised.
* The *gallery* stores reference embeddings per species. Adding a species = adding reference
  images (``SpeciesGallery.add``); no retraining of a network is required.
* Prediction = k-nearest-neighbour vote by cosine similarity. If the best similarity is below
  a threshold calibrated on validation data, the answer is ``unknown`` - the model never forces
  an out-of-gallery flower into a known class.

The embedding function is pluggable (``embed_fn``) so a stronger ONNX backbone can replace it
without changing callers.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from skimage.feature import hog, local_binary_pattern

EMBED_VERSION = "hcd-v1"          # default / fallback (no model file needed)
CNN_EMBED_VERSION = "mnv3l-v1"    # ImageNet MobileNetV3-Large features via ONNX (ai-engine/models/embed_mnv3l.onnx)
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
CROP_SIZE = 64
UNKNOWN = "unknown"
BACKGROUND = "__background__"   # reference label for real non-flower crops (USDA mask negatives); never returned
UNCERTAIN_VOTE_SHARE = 0.60     # fixed rule (not tuned): top vote share below this -> "uncertain": true


def embed_crop(rgb: np.ndarray) -> np.ndarray:
    if rgb.size == 0:
        raise ValueError("empty crop")
    c = cv2.resize(rgb, (CROP_SIZE, CROP_SIZE), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(c, cv2.COLOR_RGB2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [12, 4, 4], [0, 180, 0, 256, 0, 256]).ravel()
    hist /= max(hist.sum(), 1)
    lab = cv2.cvtColor(c, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32) / 255.0
    # centre vs. ring colour difference captures "different-coloured centre" flowers (e.g. sunflower, hibiscus)
    yy, xx = np.mgrid[:CROP_SIZE, :CROP_SIZE]
    r = np.hypot(yy - CROP_SIZE / 2, xx - CROP_SIZE / 2).ravel()
    centre, ring = lab[r < CROP_SIZE * 0.18], lab[(r > CROP_SIZE * 0.25) & (r < CROP_SIZE * 0.45)]
    moments = np.concatenate([lab.mean(0), lab.std(0), centre.mean(0) - ring.mean(0)])
    gray = cv2.cvtColor(c, cv2.COLOR_RGB2GRAY)
    h = hog(gray, orientations=9, pixels_per_cell=(16, 16), cells_per_block=(2, 2), feature_vector=True)
    lbp = local_binary_pattern(gray, 8, 1, "uniform")
    lbp_h, _ = np.histogram(lbp, bins=10, range=(0, 10))
    lbp_h = lbp_h / max(lbp_h.sum(), 1)
    parts = [hist * 3.0, moments * 2.0, h / max(np.linalg.norm(h), 1e-9), lbp_h]
    v = np.concatenate(parts).astype(np.float32)
    return v / max(np.linalg.norm(v), 1e-9)


_CNN = {}


def embed_cnn(rgb: np.ndarray) -> np.ndarray:
    """960-d pooled ImageNet features (no fine-tuning), L2-normalised. Needs onnxruntime + embed_mnv3l.onnx."""
    if rgb.size == 0:
        raise ValueError("empty crop")
    if "sess" not in _CNN:
        import onnxruntime as ort

        so = ort.SessionOptions()
        so.intra_op_num_threads = 2
        _CNN["sess"] = ort.InferenceSession(str(MODELS_DIR / "embed_mnv3l.onnx"), so, providers=["CPUExecutionProvider"])
    x = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    v = _CNN["sess"].run(None, {"image": x.transpose(2, 0, 1)[None]})[0][0].astype(np.float32)
    return v / max(np.linalg.norm(v), 1e-9)


EMBEDDERS: dict[str, Callable[[np.ndarray], np.ndarray]] = {EMBED_VERSION: embed_crop, CNN_EMBED_VERSION: embed_cnn}


def cnn_available() -> bool:
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False
    return (MODELS_DIR / "embed_mnv3l.onnx").exists()


class SpeciesGallery:
    def __init__(self, embed_fn: Callable[[np.ndarray], np.ndarray] = embed_crop, embed_version: str = EMBED_VERSION):
        self.embed_fn = embed_fn
        self.vectors: list[np.ndarray] = []
        self.labels: list[str] = []
        self.sources: list[str] = []
        self.threshold: float = 0.80
        self.k: int = 7
        self.meta: dict = {"embed_version": embed_version}

    # ---- building ----
    def add(self, species: str, rgb_crop: np.ndarray, source: str = "") -> None:
        self.vectors.append(self.embed_fn(rgb_crop))
        self.labels.append(species)
        self.sources.append(source)

    def add_vectors(self, species: str, vecs: np.ndarray, source: str = "") -> None:
        for v in vecs:
            self.vectors.append(np.asarray(v, np.float32))
            self.labels.append(species)
            self.sources.append(source)

    @property
    def species(self) -> list[str]:
        return sorted(set(self.labels) - {BACKGROUND})

    def counts(self) -> dict[str, int]:
        return {k: v for k, v in Counter(self.labels).items() if k != BACKGROUND}

    def background_references(self) -> int:
        return sum(lab == BACKGROUND for lab in self.labels)

    # ---- inference ----
    def _scores(self, q: np.ndarray) -> tuple[list[tuple[str, float]], float]:
        if not self.vectors:
            return [], 0.0
        M = np.stack(self.vectors)
        sims = M @ q
        k = min(self.k, len(sims))
        top = np.argpartition(-sims, k - 1)[:k]
        top = top[np.argsort(-sims[top])]
        votes: dict[str, float] = {}
        for i in top:
            votes[self.labels[i]] = votes.get(self.labels[i], 0.0) + float(sims[i])
        total = sum(votes.values()) or 1.0
        ranked = sorted(((s, v / total) for s, v in votes.items()), key=lambda t: -t[1])
        return ranked, float(sims[top[0]])

    def predict_vector(self, q: np.ndarray) -> dict:
        ranked, best_sim = self._scores(q)
        if not ranked:
            return {"species": UNKNOWN, "confidence": 0.0, "similarity": 0.0, "candidates": [], "uncertain": True,
                    "reason": "reference gallery is empty"}
        cands = [{"species": s, "vote_share": round(v, 4)} for s, v in ranked[:3] if s != BACKGROUND]
        sp, share = ranked[0]
        if best_sim < self.threshold:
            return {"species": UNKNOWN, "confidence": round(1 - best_sim, 4), "similarity": round(best_sim, 4),
                    "candidates": cands, "uncertain": False,
                    "reason": f"nearest reference similarity {best_sim:.3f} < open-set threshold {self.threshold:.3f}"}
        if sp == BACKGROUND:
            return {"species": UNKNOWN, "confidence": round(share, 4), "similarity": round(best_sim, 4), "candidates": cands,
                    "uncertain": False, "reason": "nearest references are background (non-flower) crops"}
        uncertain = share < UNCERTAIN_VOTE_SHARE
        return {"species": sp, "confidence": round(share, 4), "similarity": round(best_sim, 4), "candidates": cands,
                "uncertain": uncertain,
                "reason": "knn-vote" + (f"; top vote share {share:.2f} < {UNCERTAIN_VOTE_SHARE} - uncertain" if uncertain else "")}

    def predict(self, rgb_crop: np.ndarray) -> dict:
        return self.predict_vector(self.embed_fn(rgb_crop))

    # ---- persistence (npz + json; no pickle) ----
    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path.with_suffix(".npz"), vectors=np.stack(self.vectors) if self.vectors else np.zeros((0, 1)))
        path.with_suffix(".json").write_text(json.dumps({"labels": self.labels, "sources": self.sources,
                                                         "threshold": self.threshold, "k": self.k, "meta": self.meta}))

    @classmethod
    def load(cls, path: str | Path) -> "SpeciesGallery":
        path = Path(path)
        meta = json.loads(path.with_suffix(".json").read_text())
        ver = meta.get("meta", {}).get("embed_version")
        if ver not in EMBEDDERS:
            raise RuntimeError(f"gallery built with an unknown embedding version {ver!r}")
        if ver == CNN_EMBED_VERSION and not cnn_available():
            raise RuntimeError("gallery needs onnxruntime and ai-engine/models/embed_mnv3l.onnx")
        g = cls(EMBEDDERS[ver], ver)
        vec = np.load(path.with_suffix(".npz"))["vectors"]
        g.vectors = [v.astype(np.float32) for v in vec] if len(meta["labels"]) else []
        g.labels, g.sources = meta["labels"], meta["sources"]
        g.threshold, g.k, g.meta = meta["threshold"], meta["k"], meta["meta"]
        return g


def crop_box(rgb: np.ndarray, box, pad: float = 0.15) -> np.ndarray:
    h, w = rgb.shape[:2]
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    x1, y1 = int(max(0, x1 - pad * bw)), int(max(0, y1 - pad * bh))
    x2, y2 = int(min(w, x2 + pad * bw)), int(min(h, y2 + pad * bh))
    return rgb[y1:max(y2, y1 + 1), x1:max(x2, x1 + 1)]
