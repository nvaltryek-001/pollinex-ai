"""Virtual pollen-transfer simulator (deterministic, seeded particle model).

COMPUTATIONAL SIMULATION ONLY. It models geometry and simple particle physics (release, gravity,
drag, wind, turbulence, capture by a stigma target). It does not model pollen viability, stigma
receptivity, pollen-tube growth, fertilisation or fruit set. "Transfer efficiency" here means
*the fraction of simulated particles that geometrically reached the virtual stigma*.

Units: millimetres, seconds. Flower centre at origin, +z up toward the camera/effector.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np

SIM_VERSION = "pxsim-1.0"
GRAVITY = np.array([0.0, 0.0, -9810.0])  # mm/s^2
CANOPY_WIND_FACTOR = 0.02
CARRY_FRACTION = 0.75  # share of released grains that a brush / effector / insect actually carries


@dataclass
class SimParams:
    species: str = "generic"
    mode: str = "brush"                     # vibration | brush | air_assisted | cross_transfer | ring_progression | column_transfer
    particle_count: int = 150
    duration_s: float = 1.5
    dt: float = 0.005
    vibration_hz: float = 0.0
    pollen_release_rate: float = 0.5        # fraction of particles released over the run
    anther_to_stigma_mm: float = 3.0
    stigma_radius_mm: float = 0.9
    effector_offset_mm: tuple[float, float] = (0.0, 0.0)   # misalignment of the virtual effector in x,y
    wind_kmh: float = 0.0
    wind_dir_deg: float = 0.0
    humidity_pct: float | None = None
    target_spread: float = 0.0              # >0 => distributed target (e.g. strawberry receptacle)
    requires_donor: bool = False
    frames_to_record: int = 60
    seed: int = 42
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_profile(cls, species: str, profile: dict, overrides: dict | None = None) -> "SimParams":
        known = {f for f in cls.__dataclass_fields__}
        data = {k: v for k, v in profile.items() if k in known}
        data["species"] = species
        for k, v in (overrides or {}).items():
            if k in known and v is not None:
                data[k] = tuple(v) if k == "effector_offset_mm" else v
        p = cls(**data)
        p.validate()
        return p

    def validate(self) -> None:
        if not 1 <= self.particle_count <= 2000:
            raise ValueError("particle_count must be in [1, 2000]")
        if not 0.1 <= self.duration_s <= 10:
            raise ValueError("duration_s must be in [0.1, 10]")
        if not 0 <= self.pollen_release_rate <= 1:
            raise ValueError("pollen_release_rate must be in [0, 1]")
        if not 0 <= self.wind_kmh <= 120:
            raise ValueError("wind_kmh must be in [0, 120]")
        if self.anther_to_stigma_mm <= 0 or self.stigma_radius_mm <= 0:
            raise ValueError("geometry must be positive")
        if self.mode not in MODES:
            raise ValueError(f"unknown mode {self.mode}")


MODES = {"vibration", "brush", "air_assisted", "cross_transfer", "ring_progression", "column_transfer"}


def _geometry(p: SimParams, rng):
    """Return (anther_positions (N,3), stigma centre (3,), n_anthers)."""
    n_anth = {"vibration": 5, "column_transfer": 30, "ring_progression": 40}.get(p.mode, 20)
    ang = np.linspace(0, 2 * math.pi, n_anth, endpoint=False)
    if p.mode == "vibration":           # anther cone around style, stigma at the cone tip (pendant flower)
        r, z = 1.2, 0.0
        stigma = np.array([0.0, 0.0, -p.anther_to_stigma_mm])
    elif p.mode == "column_transfer":   # hibiscus: anthers along a column, stigma pads above
        r = 1.0
        z = np.linspace(-6, 0, n_anth)
        stigma = np.array([0.0, 0.0, p.anther_to_stigma_mm])
    elif p.mode == "ring_progression":  # sunflower head: pollen-presenting ring outside receptive ring
        r, z = 12.0, 0.0
        stigma = np.array([0.0, 0.0, 0.5])
    else:
        r, z = p.anther_to_stigma_mm, 0.0
        stigma = np.array([0.0, 0.0, 1.5])
    anth = np.stack([r * np.cos(ang), r * np.sin(ang), np.broadcast_to(z, ang.shape)], 1).astype(float)
    if p.mode == "cross_transfer":       # pollen arrives from a donor flower via the virtual effector
        anth = np.tile(np.array([[0.0, 0.0, 25.0]]), (n_anth, 1)) + rng.normal(0, 1.5, (n_anth, 3))
    return anth, stigma


def run_simulation(p: SimParams) -> dict:
    p.validate()
    rng = np.random.default_rng(p.seed)
    anth, stigma = _geometry(p, rng)
    n = p.particle_count
    steps = int(round(p.duration_s / p.dt))
    offset = np.array([p.effector_offset_mm[0], p.effector_offset_mm[1], 0.0])

    # ---- release schedule ----
    release_eff = p.pollen_release_rate
    notes = []
    if p.mode == "vibration":
        # release efficiency peaks in the 150-200 Hz band reported for buzz-like pollinators (Singh et al. review)
        f = p.vibration_hz
        band = math.exp(-((f - 175.0) / 60.0) ** 2) if f > 0 else 0.05
        release_eff *= band
        notes.append(f"vibration release factor {band:.2f} at {f:.0f} Hz")
    if p.humidity_pct is not None and p.humidity_pct > 85:
        release_eff *= 0.7
        notes.append("high humidity: release reduced (clumping assumption)")
    released = rng.random(n) < release_eff
    t_release = rng.uniform(0, p.duration_s * 0.6, n)

    src = anth[rng.integers(0, len(anth), n)].copy()
    pos = src.copy()
    vel = np.zeros((n, 3))
    # initial ejection velocity depends on mechanism (mm/s)
    direction = (stigma + offset) - src
    direction /= np.linalg.norm(direction, axis=1, keepdims=True) + 1e-9
    speed = {"vibration": 60.0, "brush": 35.0, "air_assisted": 80.0, "cross_transfer": 120.0,
             "ring_progression": 40.0, "column_transfer": 45.0}[p.mode]
    jitter = rng.normal(0, 0.35, (n, 3))
    v0 = (direction + jitter) * speed * rng.uniform(0.6, 1.2, (n, 1))
    if p.mode == "vibration":
        v0 += np.array([0, 0, -1.0]) * 20.0  # pendant flower: pollen falls out of the cone tip

    # free-stream wind attenuated inside the canopy / flower boundary layer (assumed factor, documented)
    w = p.wind_kmh / 3.6 * 1000.0 * CANOPY_WIND_FACTOR  # mm/s
    wind = np.array([math.cos(math.radians(p.wind_dir_deg)) * w, math.sin(math.radians(p.wind_dir_deg)) * w, 0.0])
    drag = 25.0  # 1/s - pollen is light; strong drag toward air velocity

    if p.mode == "ring_progression":
        # receptive floret ring just inside the pollen-presenting ring (protandry, centripetal opening)
        k = 60
        th = np.linspace(0, 2 * math.pi, k, endpoint=False)
        targets = np.stack([8.0 * np.cos(th), 8.0 * np.sin(th), np.full(k, stigma[2])], 1)
    elif p.target_spread > 0:
        # distributed target: random points over a dome (e.g. strawberry receptacle)
        k = 60
        th = rng.uniform(0, 2 * math.pi, k)
        rr = np.sqrt(rng.uniform(0, 1, k)) * 3.0 * p.target_spread
        targets = np.stack([rr * np.cos(th), rr * np.sin(th), stigma[2] + 0.6 * (1 - (rr / max(rr.max(), 1e-6)) ** 2)], 1)
    else:
        targets = stigma[None, :]
    distributed = p.target_spread > 0 or p.mode == "ring_progression"
    target_r = 0.6 if distributed else p.stigma_radius_mm
    guide_k = {"brush": 300.0, "column_transfer": 300.0, "ring_progression": 300.0, "cross_transfer": 40.0}.get(p.mode, 0.0)

    carried = rng.random(n) < (CARRY_FRACTION if guide_k else 0.0)
    alive = np.zeros(n, bool)
    captured = np.zeros(n, bool)
    lost = np.zeros(n, bool)
    t_capture = np.full(n, np.nan)
    min_dist = np.full(n, np.inf)
    target_hits = np.zeros(len(targets), int)
    rec_every = max(1, steps // p.frames_to_record)
    frames = []
    for s in range(steps):
        t = s * p.dt
        newly = released & ~alive & ~captured & ~lost & (t >= t_release)
        alive |= newly
        vel[newly] = v0[newly]
        idx = np.flatnonzero(alive)
        if len(idx):
            turb = rng.normal(0, 30.0, (len(idx), 3))
            acc = GRAVITY * 0.02 + drag * (wind - vel[idx]) + turb  # pollen settles slowly (Stokes regime)
            if guide_k:
                # effector / brush / insect body carries particles toward the (possibly misaligned) target
                g = carried[idx][:, None]
                if p.mode == "ring_progression":
                    nearest_t = targets[np.linalg.norm(pos[idx, None, :2] - targets[None, :, :2], axis=2).argmin(1)]
                    acc += g * ((nearest_t + offset) - pos[idx]) * guide_k
                else:
                    acc += g * ((stigma + offset) - pos[idx]) * guide_k
            vel[idx] += acc * p.dt
            pos[idx] += vel[idx] * p.dt
            d = np.linalg.norm(pos[idx, None, :] - targets[None, :, :], axis=2)
            nearest = d.argmin(1)
            dmin = d[np.arange(len(idx)), nearest]
            min_dist[idx] = np.minimum(min_dist[idx], dmin)
            hit = dmin <= target_r
            if hit.any():
                hi = idx[hit]
                captured[hi] = True
                t_capture[hi] = t
                np.add.at(target_hits, nearest[hit], 1)
            gone = (np.linalg.norm(pos[idx], axis=1) > 60) | (pos[idx, 2] < -40)
            lost[idx[gone & ~hit]] = True
            alive[idx[hit | gone]] = False
        if s % rec_every == 0:
            vis = np.flatnonzero(alive | captured)
            frames.append({"t": round(t, 4), "p": np.round(pos[vis], 2).tolist(), "c": captured[vis].astype(int).tolist()})

    n_rel = int(released.sum())
    eff = float(captured.sum() / n_rel) if n_rel else 0.0
    coverage = float((target_hits > 0).mean())
    align_err = float(np.linalg.norm(offset[:2]))
    return {
        "sim_version": SIM_VERSION, "params": {**asdict(p), "effector_offset_mm": list(p.effector_offset_mm)},
        "released": n_rel, "captured": int(captured.sum()), "lost": int(lost.sum()),
        "simulated_transfer_efficiency": round(eff, 4),
        "target_coverage": round(coverage, 4) if distributed else None,
        "alignment_error_mm": round(align_err, 3),
        "mean_time_to_capture_s": None if not captured.any() else round(float(np.nanmean(t_capture)), 4),
        "min_distance_mm": {"median": round(float(np.median(min_dist[released])), 3) if n_rel else None,
                            "p10": round(float(np.percentile(min_dist[released], 10)), 3) if n_rel else None},
        "completed": True, "notes": notes,
        "geometry": {"anthers": np.round(anth, 2).tolist(), "stigma": stigma.tolist(),
                     "targets": np.round(targets, 2).tolist(), "target_radius_mm": target_r},
        "frames": frames,
        "disclaimer": "Computational simulation of particle transfer geometry. Not evidence of fertilisation, "
                      "fruit set or yield.",
    }


def parameter_sweep(base: SimParams, name: str, values: list) -> list[dict]:
    """Run the same scenario for several values of one parameter (frames dropped)."""
    out = []
    for v in values:
        d = asdict(base)
        d[name] = tuple(v) if name == "effector_offset_mm" else v
        d["frames_to_record"] = 1
        r = run_simulation(SimParams(**d))
        out.append({name: v, "efficiency": r["simulated_transfer_efficiency"], "captured": r["captured"],
                    "released": r["released"]})
    return out
