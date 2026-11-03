# Testing Report

_Build environment: Linux, Python 3.13, 2 vCPU, no GPU. PyPI, npm and Docker Hub were **blocked**; only GitHub was reachable.
"Executed" means run in that environment; "Written, not executed" means the test exists and is wired into CI and
`scripts/run_tests.sh` but could not run there._

## Executed — passing
| Suite | Command | Result |
|---|---|---|
| AI engine unit tests (metrics, features, instance splitting, trained detector smoke, species gallery incl. open-set & persistence, stage/centre/health/pose heuristics, knowledge base, readiness incl. unknown species & environment penalties) | `python -m pytest ai-engine/tests` | **19 passed** |
| Simulation tests (all 9 species profiles, determinism, misalignment and vibration-band sensitivity, parameter validation ×4) | `python -m pytest simulation/tests` | **16 passed** |
| **Total** | | **35 / 35 passed** (≈5 s) |
| End-to-end pipeline smoke on two CC-BY fixture images (full + live mode) | ad-hoc script | ran: 86 / 66 flowers, 2.2 s / 2.8 s full, 0.8 s / 1.0 s live |
| Report generation (CSV rows, PDF bytes start with `%PDF`) with stub records | ad-hoc script | passed |
| Dataset preparation, detector training, trade-off evaluation, species evaluation | training scripts | completed; reports in `ai-engine/reports/` |
| Frontend syntax check of all `.ts/.tsx` with TypeScript 7 (no TS1xxx errors) | `tsc --noEmit … \| grep TS1` | 0 syntax errors |

## Written, not executed in the build environment
| Suite | Location | Covers |
|---|---|---|
| Backend API / DB / upload / inference (20 tests) | `backend/tests/test_api.py` | health & OpenAPI; register/login/logout & token revocation; weak/duplicate passwords; 401/403 role enforcement; upload → real inference → DB → history → image; close-up + species hint; cross-user isolation; **empty (400), non-image (415), oversized (413), too small (422), GIF (415)**; unknown species (422); live HTTP frame; live WebSocket incl. bad base64; every AI module endpoint; researcher-only reference upload; simulation create/execute/replay/409/422/sweep; fields, plants, environment validation, **weather disabled → 503 (never invented)**, pollination logs; dashboard from DB; CSV & PDF downloads; admin role change & self-demotion guard |
| Migration | CI step `alembic upgrade head` | schema creation on a fresh DB |
| Frontend unit (Vitest) | `frontend/src/test/*.test.ts(x)` | provenance badges, overlay boxes & dashed low-confidence, safe markdown (blocks `javascript:` links), camera errors (denied / not found / busy / insecure context / unsupported), error banner, auth form & password policy, API client (bearer token, FastAPI error details, **backend unavailable**) |
| E2E (Playwright, desktop + Pixel 7) | `frontend/e2e/scanner.spec.ts` | register → upload fixture → results → history; **camera permission denied** message; no horizontal overflow at 390 px |
| Type-check + production build | `npm run typecheck && npm run build` | |
| Docker builds | CI `docker` job | backend & frontend images |

## Edge cases and where they are handled
| Case | Handling | Test |
|---|---|---|
| Invalid / unsupported image | PIL verify + format allow-list → 415 | backend |
| Empty upload | 400 | backend |
| Large upload / decompression bomb | 413 size limit; `MAX_IMAGE_PIXELS` 40 MP | backend (size) |
| Camera permission denied / no camera / busy / insecure | `lib/camera.ts` error mapping, UI alert, upload fallback | vitest + e2e |
| Unknown species | gallery threshold → `unknown`; readiness `indeterminate`, no strategy | engine |
| Low confidence | per-box flag + warning when > 50 % of boxes are low-confidence; dashed overlay | engine + vitest |
| No confident detections | close-up fallback, labelled, never counted as a model detection | engine |
| Backend unavailable | API client raises "Backend unreachable", pages show retry | vitest |
| Database unavailable | `/health` reports `database: error`, status `degraded`; requests fail with 500 JSON (logged) | manual |
| Weather API unavailable | 502/503 with explicit message | backend |

## To complete verification on a networked machine
```bash
scripts/setup_dev.sh && scripts/run_tests.sh && (scripts/run_dev.sh &) && E2E=1 scripts/run_tests.sh
```
Record the outputs here and update the README audit table.
