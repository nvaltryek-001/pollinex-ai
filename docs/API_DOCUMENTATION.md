# API Reference

Base path `/api/v1`. Interactive OpenAPI/Swagger: `http://localhost:8000/docs` (ReDoc: `/redoc`).
Authentication: `Authorization: Bearer <JWT>` from `/auth/login` or `/auth/register`. Errors are `{"detail": "..."}`.

## Auth
| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/auth/register` | `{email, password, full_name?}` | ≥10 chars, upper-case + digit. First account → admin. 201 + token |
| POST | `/auth/login` | `{email, password}` | 401 on bad credentials, 403 if disabled |
| POST | `/auth/logout` | – | 204; revokes **all** of the user's tokens |
| GET | `/auth/me` | – | current user |

## Scanning
| Method | Path | Notes |
|---|---|---|
| POST | `/scans` | multipart `file` + `mode` (auto/scene/closeup), `source` (upload/camera/live), `species_hint`, `plant_id`, `field_id`, `environment_id`. 201 → scan with `flowers[]`. 400 empty · 413 too large · 415 not an image/unsupported format · 422 too small/unknown species |
| GET | `/scans?page=&page_size=&source=` | paginated history |
| GET | `/scans/{id}` | full detail |
| GET | `/scans/{id}/image` | JPEG (owner only) |
| DELETE | `/scans/{id}` | cascades |
| POST | `/scans/live/frame` | multipart frame → boxes/species/latency; not stored |
| WS | `/scans/live/ws` | send `{"token"}` then `{"frame_id","image":<base64 jpeg>}`; receive `ready` / `result` / `error` |

### Flower object (in `flowers[]`)
```json
{
  "id": 0,
  "detection": {"box": [x1,y1,x2,y2], "score": 0.83, "low_confidence": false, "method": "trained_model"},
  "species": {"species": "apple", "confidence": 0.71, "method": "trained_reference_gallery", "candidates": [...], "reason": "knn-vote"},
  "stage": {"stage": "fully_open", "score": 0.52, "distribution": {...}, "uncertain": false, "method": "heuristic"},
  "structure": {"centre_region": {...}, "yellow_cluster_visible": true, "structure_detection_available": false, "method": "heuristic"},
  "health": {"indicators": [], "status": "no_visible_anomaly_detected", "measurements": {...}},
  "pose": {"center_px": [..], "facing_estimate": "facing camera", "alignment": {"guidance": "move left / up (image space)"}, "coordinate_space": "image"},
  "readiness": {"category": "likely_ready", "confidence": 0.41, "label": "visual readiness estimate (not a validated biological prediction)",
                "strategy": {"mechanism": "cross_pollen_transfer", "recommendation": "..."}, "supporting_observations": [...],
                "uncertainty_warnings": [...], "biological_limitations": [...], "research_sources": [...], "method": "rule_engine"}
}
```

## AI modules (no persistence)
`POST /ai/detect`, `/ai/analyze`, `/ai/classify-species`, `/ai/structure`, `/ai/maturity`, `/ai/health` — multipart `file`.
`POST /ai/readiness` — JSON `{species_id, stage, stage_score?, yellow_cluster_visible?, temperature_c?, relative_humidity_pct?, rain_mm_h?, wind_kmh?}`.
`GET /ai/species` — knowledge base + gallery counts.
`POST /ai/species/{id}/references` — researcher/admin; adds a gallery image.

## Simulation
| Method | Path | Notes |
|---|---|---|
| POST | `/simulations` | `{species_id, scan_id?, overrides{particle_count, duration_s, vibration_hz, pollen_release_rate, anther_to_stigma_mm, stigma_radius_mm, effector_offset_mm, wind_kmh, wind_dir_deg, humidity_pct, seed, target_spread}}` → status `created` |
| POST | `/simulations/{id}/execute?run_async=` | runs it (sync or background) |
| GET | `/simulations`, `/simulations/{id}` | |
| GET | `/simulations/{id}/replay` | frames + geometry + disclaimer (409 if not completed) |
| POST | `/simulations/sweep` | `{species_id, parameter, values[], overrides}` |

## Records
`/fields` (GET, POST, PUT /{id}, DELETE /{id}) · `/plants` (paginated; filters `field_id`, `species_id`) ·
`/environment` (GET paginated, POST manual, DELETE) · `POST /environment/fetch {latitude, longitude, field_id?}` (Open-Meteo; 503 if disabled, 502 if provider fails) ·
`GET /environment/{id}/assessment?species_id=` · `/pollination-records` (GET, POST, PUT).

## Analytics & reports
`GET /analytics/dashboard?scope=mine|all` · `GET /analytics/species?scope=` · `GET /analytics/model-performance` ·
`GET /reports/scans.csv` · `GET /reports/summary.pdf` · `GET /reports/scans/{id}.json`. `scope=all` needs researcher/admin.

## Administration
`GET /admin/users` · `PATCH /admin/users/{id} {role?, is_active?, full_name?}` · `GET /admin/activity` ·
`GET /admin/models` (researcher/admin) · `POST /admin/models/reload` · `GET /datasets` · `GET /research/references` ·
`GET /research/documents/{name}` · `GET /health` (no auth; DB/model/storage checks).
