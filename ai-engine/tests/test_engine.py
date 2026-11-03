"""Unit tests for the AI engine (run: pytest ai-engine/tests)."""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))

from pollinex_ai.detector import MODELS_DIR, instances_from_prob  # noqa: E402
from pollinex_ai.features import N_FEATURES, pixel_features  # noqa: E402
from pollinex_ai.health import analyze_health  # noqa: E402
from pollinex_ai.knowledge import get_species, load_kb, species_ids  # noqa: E402
from pollinex_ai.maturity import STAGES, estimate_stage  # noqa: E402
from pollinex_ai.metrics import average_precision, classification_report, detection_report, iou_matrix  # noqa: E402
from pollinex_ai.pose import estimate_pose  # noqa: E402
from pollinex_ai.readiness import estimate_readiness  # noqa: E402
from pollinex_ai.species import UNKNOWN, SpeciesGallery, embed_crop  # noqa: E402
from pollinex_ai.structure import analyze_centre  # noqa: E402


def synthetic_flower(size=160, petal=(250, 250, 250), centre=(230, 200, 30), bg=(40, 120, 40), petals=5):
    img = np.full((size, size, 3), bg, np.uint8)
    c = size // 2
    for k in range(petals):
        a = 2 * np.pi * k / petals
        cv2.ellipse(img, (int(c + 0.3 * size * np.cos(a)), int(c + 0.3 * size * np.sin(a))),
                    (int(size * 0.2), int(size * 0.12)), np.degrees(a), 0, 360, petal, -1)
    cv2.circle(img, (c, c), int(size * 0.1), centre, -1)
    return img


# ---------------- metrics ----------------
def test_iou_and_perfect_ap():
    b = np.array([[0, 0, 10, 10], [20, 20, 30, 30]], float)
    assert iou_matrix(b, b).diagonal().tolist() == [1.0, 1.0]
    rep = detection_report([{"boxes": b.tolist(), "scores": [0.9, 0.8]}], [b])
    assert rep["mAP50"] == pytest.approx(1.0) and rep["mAP50_95"] == pytest.approx(1.0)


def test_ap_penalises_false_positives_and_misses():
    gt = [np.array([[0, 0, 10, 10]], float)]
    fp_first = [{"boxes": [[50, 50, 60, 60], [0, 0, 10, 10]], "scores": [0.9, 0.5]}]
    assert average_precision(fp_first, gt)["ap"] < 1.0
    miss = [{"boxes": [], "scores": []}]
    assert average_precision(miss, gt)["ap"] == 0.0


def test_classification_report_confusion():
    r = classification_report(["a", "a", "b"], ["a", "b", "b"], ["a", "b"])
    assert r["confusion_matrix"] == [[1, 1], [0, 1]]
    assert r["accuracy"] == pytest.approx(2 / 3)


# ---------------- features / instances ----------------
def test_pixel_features_shape_and_validation():
    f = pixel_features(synthetic_flower(64))
    assert f.shape == (64, 64, N_FEATURES) and f.dtype == np.float32
    with pytest.raises(ValueError):
        pixel_features(np.zeros((10, 10), np.uint8))


def test_instances_split_two_blobs():
    prob = np.zeros((100, 100), np.float32)
    cv2.circle(prob, (25, 50), 12, 1.0, -1)
    cv2.circle(prob, (75, 50), 12, 1.0, -1)
    for pdist in (0, 5):
        inst = instances_from_prob(prob, 0.5, 10, pdist)
        assert len(inst) == 2


def test_instances_empty_map():
    assert instances_from_prob(np.zeros((50, 50), np.float32), 0.5, 5, 3) == []


# ---------------- trained detector (only if model file present) ----------------
@pytest.mark.skipif(not (MODELS_DIR / "flower_pixel_hgb.joblib").exists(), reason="detector not trained")
def test_trained_detector_runs_on_synthetic_scene():
    from pollinex_ai.detector import PixelFlowerDetector
    det = PixelFlowerDetector()
    scene = np.full((480, 640, 3), (60, 110, 50), np.uint8)
    for x, y in [(120, 120), (400, 300), (520, 100)]:
        cv2.circle(scene, (x, y), 18, (245, 245, 240), -1)
    res = det.detect(scene)
    assert res.backend == "pixel-hgb-watershed" and res.latency_ms > 0
    assert all(0 <= d.score <= 1 for d in res.detections)
    for d in res.detections:
        x1, y1, x2, y2 = d.box
        assert 0 <= x1 < x2 <= 640 and 0 <= y1 < y2 <= 480


# ---------------- species gallery ----------------
def test_gallery_open_set_unknown_and_known():
    g = SpeciesGallery()
    g.threshold = 0.9
    rng = np.random.default_rng(0)
    for _ in range(5):
        g.add("whiteflower", synthetic_flower(petal=(250, 250, 250)) + rng.integers(0, 5, (160, 160, 3), dtype=np.uint8))
        g.add("redflower", synthetic_flower(petal=(200, 30, 40), centre=(250, 220, 40)))
    assert g.predict(synthetic_flower(petal=(248, 248, 248)))["species"] == "whiteflower"
    noise = rng.integers(0, 255, (160, 160, 3), dtype=np.uint8)
    assert g.predict(noise)["species"] == UNKNOWN


def test_empty_gallery_returns_unknown():
    assert SpeciesGallery().predict(synthetic_flower())["species"] == UNKNOWN


def test_gallery_save_load_roundtrip(tmp_path):
    g = SpeciesGallery()
    g.add("x", synthetic_flower())
    g.save(tmp_path / "gal")
    g2 = SpeciesGallery.load(tmp_path / "gal")
    assert g2.counts() == {"x": 1} and np.allclose(g2.vectors[0], embed_crop(synthetic_flower()))


# ---------------- heuristics ----------------
def test_stage_heuristic_outputs_valid_distribution():
    r = estimate_stage(synthetic_flower())
    assert r["stage"] in STAGES and r["method"] == "heuristic" and not r["validated"]
    assert sum(r["distribution"].values()) == pytest.approx(1.0, abs=1e-3)


def test_open_flower_vs_brown_flower_stage():
    open_ = estimate_stage(synthetic_flower(petal=(250, 250, 250)))
    brown = estimate_stage(synthetic_flower(petal=(110, 60, 20), centre=(60, 40, 20)))
    assert brown["distribution"]["senescent"] > open_["distribution"]["senescent"]


def test_structure_flags_yellow_centre_and_never_claims_detection():
    r = analyze_centre(synthetic_flower())
    assert r["structure_detection_available"] is False
    assert r["yellow_cluster_visible"] is True


def test_health_flags_browning_not_disease():
    r = analyze_health(synthetic_flower(petal=(120, 70, 25)))
    assert any(i["type"] == "browning" for i in r["indicators"])
    assert "diagnos" in r["note"].lower()


def test_pose_is_image_space():
    img = synthetic_flower(100)
    r = estimate_pose(img, [100, 100, 200, 200], (640, 480))
    assert r["coordinate_space"] == "image"
    assert 100 <= r["center_px"][0] <= 200 and r["facing_estimate"] in {"facing camera", "oblique", "side-on"}


# ---------------- knowledge base + readiness ----------------
def test_kb_has_nine_target_species_with_distinct_mechanisms():
    ids = set(species_ids())
    assert {"hibiscus", "tomato", "sunflower", "apple", "peach", "pear", "strawberry", "brinjal", "chilli"} <= ids
    mechs = {s["primary_mechanism"] for s in load_kb()["species"]}
    assert len(mechs) >= 4  # no universal method
    assert get_species("eggplant")["id"] == "brinjal"


def test_readiness_species_specific_and_labelled():
    st = {"stage": "partially_open", "score": 0.8}
    apple = estimate_readiness("apple", st)
    tomato = estimate_readiness("tomato", st)
    assert apple["category"] == "likely_ready" and tomato["category"] == "approaching"
    assert apple["strategy"]["mechanism"] != tomato["strategy"]["mechanism"]
    assert "not a validated" in apple["label"]


def test_readiness_unknown_species_is_indeterminate():
    r = estimate_readiness("unknown", {"stage": "fully_open", "score": 0.9})
    assert r["category"] == "indeterminate" and r["strategy"] is None


def test_readiness_environment_penalty():
    st = {"stage": "fully_open", "score": 0.9}
    good = estimate_readiness("tomato", st, env={"temperature_c": 24, "relative_humidity_pct": 65, "source": "manual"})
    hot = estimate_readiness("tomato", st, env={"temperature_c": 38, "relative_humidity_pct": 65, "source": "manual"})
    assert hot["confidence"] < good["confidence"]
    assert any(f["effect"] == "unfavourable" for f in hot["factors"])


def test_readiness_flags_missing_and_stale_environment():
    from datetime import datetime, timedelta, timezone
    old = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    r = estimate_readiness("apple", {"stage": "fully_open", "score": 0.9},
                           env={"temperature_c": 20, "observed_at": old, "source": "manual"})
    kinds = {f["factor"] for f in r["factors"]}
    assert {"missing_data", "stale_data"} <= kinds
    assert any("incomplete or out of date" in w for w in r["uncertainty_warnings"])
    naive = estimate_readiness("apple", {"stage": "fully_open", "score": 0.9},
                               env={"temperature_c": 20, "relative_humidity_pct": 60, "rain_mm_h": 0, "wind_kmh": 5,
                                    "observed_at": datetime.utcnow().isoformat(), "source": "manual"})
    assert not any(f["factor"] in ("missing_data", "stale_data") for f in naive["factors"])


def test_structure_lists_every_structure_with_honest_status():
    r = analyze_centre(synthetic_flower())
    st = {x["structure"]: x["status"] for x in r["structures"]}
    assert st["petals"] == "heuristic_region"
    assert all(st[k] == "not_ai_validated" for k in ("anther", "stigma", "stamen", "pistil"))
