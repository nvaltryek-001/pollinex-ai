import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "simulation"), str(ROOT / "ai-engine")]

from pollinex_ai.knowledge import load_kb  # noqa: E402
from pollinex_sim import SimParams, parameter_sweep, run_simulation  # noqa: E402


@pytest.mark.parametrize("species", [s["id"] for s in load_kb()["species"]])
def test_every_species_profile_runs(species):
    sp = next(s for s in load_kb()["species"] if s["id"] == species)
    r = run_simulation(SimParams.from_profile(species, sp["simulation_profile"]))
    assert r["completed"] and 0 <= r["simulated_transfer_efficiency"] <= 1
    assert r["captured"] <= r["released"] <= sp["simulation_profile"]["particle_count"]
    assert "Not evidence of fertilisation" in r["disclaimer"]
    assert len(r["frames"]) > 0


def test_deterministic_with_seed():
    p = SimParams(mode="vibration", vibration_hz=175, seed=3, frames_to_record=2)
    a, b = run_simulation(p), run_simulation(p)
    assert a["captured"] == b["captured"] and a["frames"] == b["frames"]


def test_misalignment_reduces_transfer():
    rows = parameter_sweep(SimParams(mode="brush", particle_count=200, seed=1), "effector_offset_mm", [(0, 0), (4, 0)])
    assert rows[0]["efficiency"] > rows[1]["efficiency"]


def test_vibration_band_matters():
    rows = parameter_sweep(SimParams(mode="vibration", particle_count=300, pollen_release_rate=1.0, seed=2),
                           "vibration_hz", [175, 600])
    assert rows[0]["released"] > rows[1]["released"]


@pytest.mark.parametrize("bad", [{"particle_count": 0}, {"duration_s": 50}, {"wind_kmh": -1}, {"mode": "teleport"}])
def test_validation(bad):
    with pytest.raises(ValueError):
        run_simulation(SimParams(**bad))
