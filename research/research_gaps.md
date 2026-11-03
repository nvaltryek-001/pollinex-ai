# Research Gaps and How POLLINEX AI Responds

Each gap is grounded in the reviewed literature (see `literature_review.md`). Our response is an **engineering
contribution**, not a validated scientific result.

## Gap 1 — Crop-specific systems, no shared species-aware decision layer
Singh et al. (2025) note that robot pollinators are usually tailored to one crop; Broussard et al. (2023) show that the
right method differs by crop (vibration for self-compatible tomato vs. compatible cross-pollen for apple/pear).

**Response.** A data-driven species knowledge base (`species_kb.json`) plus a rule engine that selects a
mechanism per species and explains why. New species are added by adding a JSON entry and (optionally) reference
images — no code change.

## Gap 2 — Perception research rarely ships an accessible, honest tool
FloPE and the reviewed robot systems require robots, RGB-D cameras or 3D reconstruction; EWD's detector targets
ecologists' overview images. Growers and students lack a phone-based tool that states its own uncertainty.

**Response.** A browser scanner (upload + phone/laptop camera with adjustable frame sampling) backed by local CPU
inference. Every result is tagged *trained model*, *heuristic*, *rule* or *simulation*, with low-confidence warnings.

## Gap 3 — Missing labelled data for reproductive structures and flower stages
We found no openly licensed, reachable dataset with anther/stigma annotations or bud→senescence stage labels for
the nine target crops. EWD and the USDA set label whole flowers only.

**Response.** (a) We do **not** claim anther/stigma detection; the structure module is an explicitly labelled
colour/geometry heuristic for the flower *centre region* only. (b) We ship a CVAT-based annotation workflow,
label schema and YOLO training script so that a structure/stage model can be trained once data exists.

## Gap 4 — Environmental context is rarely joined to visual readiness
Broussard et al. note temperature, humidity and flower age are often ignored in pollination trials.

**Response.** Environmental records (manual or Open-Meteo with source + timestamp) are attached to scans and enter
the readiness rules as *modifiers*, never as proof.

## Gap 5 — Simulation outputs are easily confused with biological outcomes
**Response.** The simulator reports *geometric transfer efficiency* only, and the UI/report separate: detection
metrics · simulation completion · simulated transfer efficiency · biological outcome (always "not measured").
