# Testing Report

> **2026-11-04, final release:** CI run 41764626714 on `ef89228`, the first commit with YOLO11n ONNX deployed and the 6-species gallery. All 5 jobs passed:
>
> | Job | Result |
> |---|---|
> | AI engine + simulator | 43 passed |
> | Backend | 24 passed |
> | Vitest | 11 passed |
> | Type-check and build | ✅ |
> | Playwright | 14 passed |
> | Docker | ✅ |
> | Windows fresh clone | 43 / 24 / 11 / 12 passed (2 skipped by design) |
>
> Details: `FINAL_RELEASE_REPORT.md` §6.

_Last updated 2026-11-03 (session 3)._

## Where the tests ran
The development workspace could not reach PyPI, npm or Docker Hub, so the full stack is verified by **GitHub Actions**
(`.github/workflows/ci.yml`) on every push to `main`: clean Ubuntu and Windows runners that install the real packages from
`backend/requirements.txt` and `frontend/package.json`. Reference runs: **#41626877962** (`b8be26d`) and the latest **#41628075012** (`baa8ae6`,
<https://github.com/nvaltryek-001/pollinex-ai/actions/runs/41628075012>), all 5 jobs green in both.
Re-run anytime: GitHub → Actions → CI → *Run workflow*, or locally with `scripts\test_windows.ps1 -E2E`.

## Summary (run #41626877962)
| Suite | Where | Tests | Result |
|---|---|---|---|
| Ruff lint (errors: F, E9, PLE) | Ubuntu | all Python | ✅ pass |
| AI engine unit tests | Ubuntu + Windows (+ workspace) | 21 | ✅ 21 passed |
| Simulator tests | Ubuntu + Windows (+ workspace) | 16 | ✅ 16 passed |
| Backend API / auth / roles / DB / uploads / inference / rate limit / startup seeding | Ubuntu (SQLite) + Windows | 24 | ✅ 24 passed |
| Alembic `0001 → 0002` upgrade, downgrade to base, upgrade again | Ubuntu, SQLite | 1 | ✅ pass |
| Alembic upgrade on **PostgreSQL 16** (+ table listing, 20 tables) | Ubuntu service container | 1 | ✅ pass |
| **Backend startup** (uvicorn, `POLLINEX_ENV=production`, PostgreSQL) → `/api/v1/health` = ok, `/docs` served | Ubuntu | 1 | ✅ pass |
| Frontend type-check (`tsc --noEmit`, strict) | Ubuntu + Windows | — | ✅ pass |
| Frontend unit/component tests (Vitest) | Ubuntu + Windows | 11 | ✅ 11 passed |
| **Production build** (`vite build`, 2,210 modules) | Ubuntu + Windows | — | ✅ pass |
| **Playwright E2E**, desktop Chrome + Pixel 7, Chromium fake camera | Ubuntu | 14 | ✅ 14 passed |
| Docker images (backend, frontend) | Ubuntu | 2 | ✅ built |
| **Docker Compose smoke test** (PostgreSQL + API + nginx): API health ok, web page served, `/api` proxied | Ubuntu | 1 | ✅ pass |
| **Windows**: `setup_windows.ps1` on a fresh clone (Python 3.12, Node 22) → dependency check "all required checks passed" | windows-latest | — | ✅ pass |
| **Windows**: `test_windows.ps1 -E2E` (7 steps, all PASS; Playwright 12 passed + 2 screenshot tests skipped by design) | windows-latest | — | ✅ pass |
| **Windows**: backend starts with uvicorn → `/api/v1/health` ok | windows-latest | — | ✅ pass |

## Playwright E2E tests (each on desktop **and** mobile)
1. Register → upload `tests/fixtures/sample_orchard.jpg` → real detections with provenance badges → **manual species correction** → history.
2. **Camera starts** (Chromium fake device) → **live scan analyses sampled frames** (WebSocket/HTTP) → *Capture & analyse* saves a scan.
3. **Camera permission denied** → clear error message.
4. Simulator runs, replays and shows the computational disclaimer / "not measured" biological outcome.
5. **Every sidebar page (17)** loads without an error banner.
6. No horizontal overflow at 390 px (responsive layout).
7. Screenshot capture (`SCREENSHOTS=1`) → `docs/screenshots/`.

## Backend tests (24)
Health/OpenAPI · register/login/logout + token revocation · weak/duplicate passwords · 401 without token · role enforcement ·
**standard user gets 403 on 7 admin/researcher endpoints** · upload → inference → DB → history → image · close-up + species hint ·
cross-user isolation (404) · empty (400), non-image (415), oversized (413), too small (422), GIF (415) · unknown species (422) ·
live HTTP frame · live WebSocket incl. bad base64 · all AI module endpoints · researcher-only reference upload ·
**manual species correction** (keeps original, re-runs readiness, 404/422) · simulation create/execute/replay/409/422/sweep ·
fields/plants/environment validation · weather disabled → 503 (never invented) · pollination logs · dashboard from DB ·
CSV + PDF downloads · admin role change + self-demotion guard · **rate limit → 429** · startup seeding/health.

## Failures found and fixes applied
| Session | Where | Failure | Fix |
|---|---|---|---|
| 1 | engine | close-up flower mask empty → browning not measured | border-colour background model before GrabCut |
| 1 | data | upstream boxes vertically flipped → near-zero mAP | ground truth re-derived from masks (documented audit) |
| 2 | engine | naive SQLite timestamps crashed data-age check | naive treated as UTC + test |
| 3 | CI typecheck | `api.test.ts`: `err` is `unknown` (TS18046) | typed the caught error (also found by the workspace audit type-check) |
| 3 | CI backend | `test_manual_species_correction…` got 401: earlier admin test changes that user's role, which revokes their token by design | test uses its own account; asserts 201 |
| 3 | CI vitest | markdown test looked for an element whose whole text is "bad" | assert no anchor is created for the `javascript:` link (behaviour was already correct) |
| 3 | backend | Starlette deprecations for 413/422 constants | numeric status codes |
| 3 | Windows | PowerShell 5.1 can abort on harmless native stderr with `Stop` | scripts use `Continue` + explicit exit-code checks |
| 3 | ruff | unused f-string | fixed |

## Known warnings (non-failing)
Starlette recommends `httpx2` for its TestClient; React Router v7 future-flag notices; Node `punycode` deprecation from a transitive
npm dependency; GitHub's Node-20 action runtime notice.

## Remaining limitations
* Real phone hardware is not automated: camera code is verified with Chromium's fake device and a Pixel 7 emulation profile;
  run the manual phone check in `docs/NEXT_SESSION_TASKS.md` (HTTPS needed on a phone).
* Database-unavailable behaviour (`/health` → `degraded`) is implemented but has no automated test.
* Open-Meteo is never called in CI (disabled → 503 path is tested); the live provider path is manual.
