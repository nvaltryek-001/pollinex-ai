# Project Completion Audit

_Audit date: 2026-11-03 (session 2). Baseline: commit `006e3c7`. Scope: every folder in the repository, the 8 milestone
commits, README and docs. Build environment: PyPI, npm, Docker Hub and Open-Meteo were **unreachable**, so anything that
needs third-party web packages could be inspected but not executed._

Legend: ✅ done & executed · 🟢 done, code-reviewed, **not executed here** · 🟡 partial · ❌ missing · 🔧 fixed/added this session

## 1. Existing functionality (as found)
| Area | Status | Evidence |
|---|---|---|
| Research docs (review, comparison, gaps, methodology, BibTeX/JSON refs) | ✅ | `research/` |
| USDA dataset preparation, splits, leakage + box-orientation audit | ✅ | `datasets/reports/usda_fruit_flower_report.*` |
| CPU flower detector, baseline, ablation, speed study | ✅ | test mAP@0.5 0.410 (deployed config) — **historical result** of session 1 |
| Open-set species gallery + evaluation | ✅ | `ai-engine/reports/species_evaluation.json` |
| Stage / centre / health / pose heuristics | ✅ (labelled heuristic) | unit tests |
| Knowledge base (9 species) + readiness engine | ✅ | unit tests |
| Particle simulator (6 modes) | ✅ | 16 tests |
| FastAPI backend (auth, scans, live WS, AI, simulations, records, analytics, reports, admin) | 🟢 | 20 API tests written |
| React app, 20 pages, scanner, Three.js | 🟢 | syntax-checked only |
| Docker / Compose / Render / Vercel / CI | 🟢 | not built |
| Windows setup | ❌ | only bash scripts |

## 2. Placeholder / fake-data search
`grep` for TODO, FIXME, mock, placeholder, hard-coded metrics across `backend/`, `ai-engine/`, `simulation/`, `frontend/src`:
**none found** in application code (only test mocks and HTML `placeholder=` attributes). All dashboard numbers come from the DB or
`ai-engine/reports/*.json`.

## 3. Disconnected features / gaps found and resolved this session
| # | Gap vs. master prompt | Resolution | Status |
|---|---|---|---|
| 1 | No **manual species correction** | `PATCH /scans/{id}/flowers/{i}/species`; keeps `species_original`; re-runs readiness; UI selector; migration `0002` | 🔧🟢 |
| 2 | No **rate limiting** | sliding-window limiter on login (20/5 min/IP), register (10/h/IP), scans (30/min/user), live frames (120/min/user) | 🔧🟢 |
| 3 | Environment: no **weather condition**, no **missing/stale-data warnings** | Open-Meteo `weather_code` → WMO text; readiness factors `missing_data`, `stale_data` (> 6 h) + warning; UI column | 🔧✅ engine / 🟢 API |
| 4 | Analytics lacked **environmental trends** and **simulation history** | added to `/analytics/dashboard` + Analytics page charts/table | 🔧🟢 |
| 5 | Simulator lacked **speed control** and visible species structures | 0.25–4× playback, anther cone / donor flower / receptacle / floret rings / staminal column with labels, particle trails, per-mode explanation | 🔧🟢 |
| 6 | Reproductive structures listed only implicitly | per-structure status table (petals/centre = heuristic region; anther/stigma/stamen/pistil = **not AI-validated**) | 🔧✅ |
| 7 | No **notifications** | toast system on scan, simulation, environment and pollination-record actions | 🔧🟢 |
| 8 | No Windows scripts | `scripts/setup_windows.ps1`, `run_windows.ps1`, `test_windows.ps1` | 🔧 (not run on Windows here) |
| 9 | Docs names | `ARCHITECTURE.md`, `API_DOCUMENTATION.md` (renamed), new `SIMULATOR_DOCUMENTATION.md`, Colab GPU guide | 🔧 |
| 10 | Admin-endpoint access by standard users untested | new test covering 7 protected endpoints | 🔧🟢 |

## 4. Known bugs / risks (unverified until the stack runs)
| Risk | Why | Mitigation |
|---|---|---|
| Frontend type errors or library API drift (React Router 6, Recharts 2, Three r170 OrbitControls import path) | never compiled against installed types | `npm run typecheck` in CI / `test_windows.ps1` |
| SQLAlchemy pagination count over a `select(Scan)` with `lazy="joined"` relationships | not executed | covered by `test_scan_upload_runs_real_inference_and_persists` |
| scikit-learn pickle compatibility (detector saved with 1.9.1) | pin may not exist for every Python/OS | pinned in requirements; retrain script (~30 min CPU) |
| In-memory rate limiter | per-process only | documented; proxy-level limits for multi-worker deploys |
| Detector precision 0.17 on cluttered scenes | CPU model, unlabelled background blossoms | YOLO11 recipe + Colab guide |

## 5. Required improvements still open
1. **Execute** backend (24 tests), frontend unit (Vitest), E2E (Playwright), production build, Docker builds — blocked here.
2. Screenshots for README (need a running frontend).
3. YOLO11 training run (GPU, optional) and comparison on the same test split.
4. Reference images + held-out tests for hibiscus, tomato, sunflower, strawberry, brinjal, chilli.
5. Structure/stage datasets via the CVAT workflow → trained models.
6. Deployment (free tiers) and recording of URLs.

## 6. Completion status
| Area | % |
|---|---|
| Research & documentation | 95 |
| Dataset engineering | 85 |
| AI engine (trained + heuristics, honest scope) | 75 |
| Simulator (engine + 3-D UI code) | 85 |
| Backend code | 90 (unexecuted) |
| Frontend code | 85 (unbuilt) |
| Verification (executed tests/builds) | 35 |
| Deployment | 20 (configs only) |
| **Overall honest estimate** | **≈ 72 %** |

The remaining ≈ 28 % is dominated by *execution*: building, running and fixing the web stack, which requires package-registry
access. See `docs/NEXT_SESSION_TASKS.md`.
