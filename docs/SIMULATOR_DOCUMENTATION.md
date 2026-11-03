# Virtual Pollination Simulator

Code: `simulation/pollinex_sim/engine.py` (physics, Python) · `frontend/src/components/SimScene.tsx` (Three.js + 2-D canvas) ·
`frontend/src/pages/Simulator.tsx` (controls) · API `/api/v1/simulations/*`.

> **Three things are kept separate everywhere:** (1) *visual detection* (camera models), (2) *computationally simulated
> pollen transfer* (this module), (3) *actual biological pollination and fertilisation* (never measured by POLLINEX).
> The result panel shows four tiles — detection accuracy (n/a here), simulation completion, simulated transfer efficiency,
> biological outcome ("not measured") — and the API returns a disclaimer with every replay.

## Model
Units: millimetres and seconds; flower centre at the origin, +z towards the viewer/effector. Deterministic for a given seed.

| Step | Implementation |
|---|---|
| Geometry | per mode: anther positions, stigma/target positions, target radius |
| Release | each particle released with probability `pollen_release_rate × factors`, at a random time in the first 60 % of the run |
| Vibration factor | `exp(-((f − 175)/60)²)` — peaks in the 150–200 Hz band reported for buzz-like pollinators (Singh et al., 2025) |
| Humidity factor | × 0.7 above 85 % RH (pollen clumping assumption) |
| Motion | explicit Euler, dt = 5 ms: reduced gravity (Stokes settling), drag towards wind (canopy attenuation 0.02 of free-stream), Gaussian turbulence |
| Guided transport | brush / contact / effector modes pull a *carried* subset (75 %) towards the effector aim point = stigma + misalignment offset |
| Capture | particle within the target radius → captured (counts per target for coverage) |
| Loss | > 60 mm from the flower or below −40 mm |

**Outputs:** released, captured, lost, *simulated transfer efficiency* (captured ÷ released), target coverage (distributed targets),
alignment error, mean time to capture, min-distance statistics, recorded frames (≈60) and geometry for replay.

## Species profiles (from `species_kb.json → simulation_profile`)
| Species | Mode | Representation |
|---|---|---|
| Tomato, Brinjal | `vibration` | pendant flower, fused poricidal anther cone, stigma at the cone tip; release depends on vibration frequency |
| Apple, Pear | `cross_transfer` | separate **donor flower of a compatible cultivar** above the target; pollen carried to the target stigma (self-pollen not modelled as effective) |
| Chilli, Peach | `brush` | anther ring → central stigma within the same flower |
| Strawberry | `air_assisted` | domed receptacle with **60 pistil targets**; reports coverage because unfertilised pistils give misshapen fruit |
| Sunflower | `ring_progression` | capitulum with an outer pollen-presenting ring and an inner **ring of 60 receptive florets** (protandry) |
| Hibiscus | `column_transfer` | anthers along the **staminal column**, **five stigma pads** at its tip |

## Controls (UI)
Species profile · vibration Hz (vibration modes) · particle count (20–600) · release rate · effector offset x/y (alignment) ·
wind speed & direction · humidity · random seed · **Run** · play / pause / replay · timeline scrubbing · **playback speed 0.25–4×** ·
3-D ↔ 2-D toggle (2-D side projection is used automatically when WebGL is unavailable) · parameter sweeps (alignment, wind, Hz)
with a chart · history with replay.

3-D scene: schematic petals, species-specific structures with text labels, anthers (amber), receptive targets (green), effector aim
ring (red), particles (amber in flight with short trails, green when captured), orbit controls.

## Assumptions and limitations
* Parameters (canopy wind factor 0.02, carry fraction 0.75, reduced gravity, drag 25 s⁻¹, release band 175 ± 60 Hz) are modelling
  assumptions chosen for plausible behaviour, **not fitted to measurements**.
* Geometry is schematic and not to scale for any cultivar.
* No pollen viability, stigma receptivity, self-incompatibility genetics, pollen-tube growth, fertilisation or fruit set.
* Efficiency values are only comparable between runs of the same profile and seed (use sweeps for sensitivity, not absolute claims).

## Tests (`simulation/tests/test_simulation.py`, executed)
All nine profiles run and stay within bounds · determinism for a fixed seed · misalignment reduces transfer · out-of-band vibration
reduces release · invalid parameters are rejected (4 cases).
