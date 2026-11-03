# Testing Report

_Last updated 2026-11-03 (session 2). Environment: Linux, Python 3.13.18, 2 vCPU, no GPU. **PyPI, npm and Docker Hub were
blocked**, so only suites whose dependencies were pre-installed could run. "Executed" = run here with the result shown.
"Not executed" = written and wired into CI / `scripts/test_windows.ps1`, but **no result is claimed**._

## Summary
| Suite | Tests | Status | Result |
|---|---|---|---|
| AI engine unit tests (`ai-engine/tests`) | 21 | executed | **21 passed** |
| Simulator tests (`simulation/tests`) | 16 | executed | **16 passed** |
| Backend API / auth / DB / upload / inference / roles / rate-limit / startup (`backend/tests`) | 24 | **not executed** (FastAPI, SQLAlchemy not installable) | — |
| Alembic migrations 0001 → 0002 | 1 | **not executed** | — |
| Frontend type-check | — | **not executed** (npm blocked) | — |
| Frontend unit + component tests (Vitest) | 11 | **not executed** | — |
| Playwright E2E (desktop + Pixel 7) | 3 × 2 | **not executed** | — |
| Production frontend build | — | **not executed** | — |
| Backend startup | — | **not executed** (startup code path covered by backend tests) | — |
| Docker image builds | 2 | **not executed** (no Docker daemon/registry) | — |

Ad-hoc executed checks: end-to-end Python pipeline on both fixture images (session 1: 86 / 66 flowers, 2.2 s / 2.8 s full,
0.8 s / 1.0 s live); CSV/PDF report generation with stub records (session 1); TypeScript syntax check of all sources (session 1).

## Executed tests (individual results)
| Test | Package | Status | Result |
|---|---|---|---|
| `test_iou_and_perfect_ap` | ai-engine | executed | PASS |
| `test_ap_penalises_false_positives_and_misses` | ai-engine | executed | PASS |
| `test_classification_report_confusion` | ai-engine | executed | PASS |
| `test_pixel_features_shape_and_validation` | ai-engine | executed | PASS |
| `test_instances_split_two_blobs` | ai-engine | executed | PASS |
| `test_instances_empty_map` | ai-engine | executed | PASS |
| `test_trained_detector_runs_on_synthetic_scene` | ai-engine | executed | PASS |
| `test_gallery_open_set_unknown_and_known` | ai-engine | executed | PASS |
| `test_empty_gallery_returns_unknown` | ai-engine | executed | PASS |
| `test_gallery_save_load_roundtrip` | ai-engine | executed | PASS |
| `test_stage_heuristic_outputs_valid_distribution` | ai-engine | executed | PASS |
| `test_open_flower_vs_brown_flower_stage` | ai-engine | executed | PASS |
| `test_structure_flags_yellow_centre_and_never_claims_detection` | ai-engine | executed | PASS |
| `test_health_flags_browning_not_disease` | ai-engine | executed | PASS |
| `test_pose_is_image_space` | ai-engine | executed | PASS |
| `test_kb_has_nine_target_species_with_distinct_mechanisms` | ai-engine | executed | PASS |
| `test_readiness_species_specific_and_labelled` | ai-engine | executed | PASS |
| `test_readiness_unknown_species_is_indeterminate` | ai-engine | executed | PASS |
| `test_readiness_environment_penalty` | ai-engine | executed | PASS |
| `test_readiness_flags_missing_and_stale_environment` | ai-engine | executed | PASS |
| `test_structure_lists_every_structure_with_honest_status` | ai-engine | executed | PASS |
| `test_every_species_profile_runs[tomato]` | simulation | executed | PASS |
| `test_every_species_profile_runs[brinjal]` | simulation | executed | PASS |
| `test_every_species_profile_runs[chilli]` | simulation | executed | PASS |
| `test_every_species_profile_runs[apple]` | simulation | executed | PASS |
| `test_every_species_profile_runs[pear]` | simulation | executed | PASS |
| `test_every_species_profile_runs[peach]` | simulation | executed | PASS |
| `test_every_species_profile_runs[strawberry]` | simulation | executed | PASS |
| `test_every_species_profile_runs[sunflower]` | simulation | executed | PASS |
| `test_every_species_profile_runs[hibiscus]` | simulation | executed | PASS |
| `test_deterministic_with_seed` | simulation | executed | PASS |
| `test_misalignment_reduces_transfer` | simulation | executed | PASS |
| `test_vibration_band_matters` | simulation | executed | PASS |
| `test_validation[bad0]` | simulation | executed | PASS |
| `test_validation[bad1]` | simulation | executed | PASS |
| `test_validation[bad2]` | simulation | executed | PASS |
| `test_validation[bad3]` | simulation | executed | PASS |

## Failures found and fixes applied
| Session | Failure | Fix |
|---|---|---|
| 1 | `test_health_flags_browning_not_disease`: close-up flower mask came out empty (GrabCut on a uniform background), so browning was not measured | added a border-colour background model before GrabCut in `regions.crop_flower_mask` |
| 1 | Detector ground truth mismatched the images (upstream boxes vertically flipped) → near-zero mAP | instances re-derived from masks; audit recorded in the dataset report |
| 2 | Readiness crashed on naive (SQLite) timestamps when computing data age | treat naive timestamps as UTC; covered by `test_readiness_flags_missing_and_stale_environment` |

## Not-executed suites: what they cover
* **Backend (24)**: health/OpenAPI; register/login/logout + token revocation; weak & duplicate passwords; 401/403; **standard user
  blocked from 7 admin/researcher endpoints**; upload → inference → DB → history → image; close-up + species hint; cross-user isolation;
  empty (400), non-image (415), oversized (413), too small (422), GIF (415); unknown species (422); live HTTP frame; live WebSocket
  incl. bad base64; all AI module endpoints; researcher-only reference upload; **manual species correction** (re-runs readiness,
  keeps original, 404/422); simulation create/execute/replay/409/422/sweep; fields/plants/environment validation; weather disabled
  → 503; pollination logs; dashboard from DB; CSV/PDF; admin role change + self-demotion guard; **rate limit → 429**; startup seeding.
* **Vitest (11)**: provenance badges, overlay boxes & dashed low-confidence, safe markdown, camera errors (denied / not found /
  busy / insecure / unsupported), error banner, auth form, API client (token, error detail, backend unreachable).
* **Playwright (3 per device)**: register → upload → results → history; camera permission denied; no horizontal overflow at 390 px.

## Remaining limitations
Nothing in the web stack has been executed. Run `scripts/test_windows.ps1 -E2E` (or `E2E=1 scripts/run_tests.sh`) and replace the
"not executed" rows with real results. Database-unavailable behaviour is implemented (`/health` → `degraded`) but has no automated test.
