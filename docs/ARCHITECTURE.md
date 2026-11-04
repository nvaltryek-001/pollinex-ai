# System Architecture

## Service boundaries

| Component | Path | Depends on | Responsibility |
|---|---|---|---|
| Web app | `frontend/` | REST + WebSocket API | UI, camera capture, frame sampling, overlays, Three.js replay |
| API | `backend/app` | ai-engine, simulation, DB, file storage | Auth, validation, persistence, orchestration, reports |
| AI engine | `ai-engine/pollinex_ai` | NumPy/SciPy/OpenCV/scikit-learn | All image analysis + knowledge base + readiness rules; no web or DB code |
| Simulation | `simulation/pollinex_sim` | NumPy | Seeded particle simulation; no web or DB code |
| Training | `ai-engine/training`, `datasets/scripts` | the above (+ optional PyTorch) | Offline dataset prep, training, evaluation |

The AI engine and simulator are plain Python packages with their own tests, so they can be used from notebooks/CLI or
swapped behind the API without touching the web layer.

## Request flow: image scan

```mermaid
sequenceDiagram
  participant B as Browser
  participant A as FastAPI /scans
  participant S as storage
  participant E as ai-engine Analyzer
  participant D as DB
  B->>A: multipart image (+mode, species_hint, env, plant)
  A->>S: validate (format, size, pixels) · EXIF transpose · re-encode JPEG (strip GPS) · sha256 path
  A->>E: analyze(rgb) in threadpool (serialised by a lock)
  E->>E: detector → instances (or close-up fallback)
  loop top-25 flowers
    E->>E: species gallery · stage · centre · health · pose · readiness(KB, env)
  end
  E-->>A: result with per-field provenance
  A->>D: scan + detections + maturity/structure/readiness rows + activity log
  A-->>B: ScanDetail JSON → overlay + cards
```

## Species decision inside the analyzer (auto mode)

```mermaid
flowchart LR
  I[uploaded photo] --> DET[YOLO11n ONNX<br/>class: flower]
  DET -->|confident boxes| C[box crop + 10 % pad]
  DET -->|none| F[close-up fallback:<br/>centre 80 % = one flower]
  I --> SC[centre 80 % of photo]
  C --> EC[MobileNetV3 embedding]
  SC --> ES[MobileNetV3 embedding]
  F --> EF[MobileNetV3 embedding]
  EC --> V1[k-NN votes]
  ES --> V2[k-NN votes]
  V1 & V2 --> B["blend: 0.25 x crop + 0.75 x photo<br/>(weight chosen on validation)"]
  EF --> V3[k-NN votes]
  B & V3 --> R{top vote}
  R -->|enabled species| SP[species + confidence + support status]
  R -->|background or strawberry refs,<br/>or similarity below threshold| U[unknown + reason]
  SP & U --> RULES[stage / centre / health heuristics<br/>-> readiness rules + species KB]
```

## Data and training flow

```mermaid
flowchart TB
  subgraph Sources [licensed sources]
    USDA[USDA fruit flower<br/>CC BY 4.0, boxes]
    TF[TF Flower Detection<br/>sunflower, CC BY 4.0, boxes]
    INAT[iNaturalist<br/>CC0/BY/BY-SA, image labels]
    COM[Wikimedia Commons<br/>CC0/BY/BY-SA/PD, image labels]
  end
  Sources --> AUD[dataset_quality_audit.py<br/>decode, duplicates, leakage]
  AUD --> SPL[grouped train / val / test<br/>+ leakage exclusions]
  SPL -->|boxes only| YOLO[train_yolo11.py -> select on val -> deploy rule -> ONNX]
  SPL -->|crops / photos| GAL[build_species_gallery_multi.py<br/>gate on val]
  GAL --> CTX[species_context_rule.py<br/>species_unsupported_rule.py<br/>chosen on val]
  SPL -->|image-level photos| PROP[propose_species_boxes.py<br/>UNVERIFIED proposals]
  PROP --> CVAT[human review in CVAT]
  CVAT --> IMP[import_verified_boxes.py] --> SD[train_species_detector.py<br/>gated: pending]
  YOLO & CTX --> EVAL[evaluate_deployed_models.py<br/>test, once]
```

## Live scanning
* Client samples one frame every *N* ms (0.5–5 s, user-adjustable). A new frame is **only sent when the previous result
  arrived** (back-pressure); skipped ticks are counted and shown.
* Transport: WebSocket `/scans/live/ws` (first message = JWT), automatic fallback to `POST /scans/live/frame`.
* Server runs the detector in **fast mode** (800 px, chosen on validation) and skips heuristics; nothing is persisted.
  "Capture & analyse" runs the full pipeline and stores a scan.

## Detector backends
`load_default_detector()` prefers `ai-engine/models/flower_yolo11n.onnx` (onnxruntime) and otherwise loads the CPU
pixel model `flower_pixel_hgb.joblib`. Both return identical `Detection` objects. `/admin/models/reload` re-reads files after
retraining.

## Concurrency & resources
* Inference runs in Starlette's threadpool; a process-wide lock serialises analyses to bound RAM on laptops.
* Simulations execute synchronously (≈50 ms) or as a background task (`?run_async=true`).
* Images ≤ 15 MB (configurable), ≤ 40 MP, downscaled to ≤ 2560 px for storage.

## Security
JWT (HS256) with per-user `token_version` (logout/role change revokes tokens); PBKDF2-SHA256 600k iterations; role checks via
dependencies; ownership checks on every record; upload validation & metadata stripping; path traversal guard on file
serving; security headers; CORS allow-list; secrets only via environment. See `SECURITY.md`.

## Extending to new species
1. Add an entry to `ai-engine/pollinex_ai/knowledge/species_kb.json` (mechanism, stages, strategy, simulation profile, evidence).
2. Add reference images through *Species recognition → Add reference* (researcher/admin).
3. Optionally collect annotated images with `datasets/annotation/` and train YOLO11.
No code changes are required for steps 1–2.
