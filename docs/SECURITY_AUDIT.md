# Security audit (2026-11-04)

Each control is checked against the code. Dependency findings come from the `Security (dependency audit)` workflow
(run 41857674397). It runs weekly and on demand.

## Controls
| Area | Implementation | Evidence |
|---|---|---|
| Passwords | PBKDF2-HMAC-SHA256, 600,000 iterations; policy of ≥ 10 characters with an uppercase letter and a digit | `security.py`; backend tests |
| Tokens | JWT HS256 with expiry. `token_version` revokes every earlier token on logout, password change or role change | `test_login_logout_revokes_token`, `test_profile_update_and_password_change` |
| Secrets | Production refuses to start without `JWT_SECRET` and rejects placeholder secrets. `.env` is git-ignored. The Render secret exists only in the Render dashboard | `config.py` |
| Authorisation | Roles admin / researcher / user. Every scan, plant and record query is filtered by owner; `scope=all` needs researcher or admin | `test_scan_isolation_between_users`, admin tests |
| Rate limiting | Registration 10/hour per IP, login 20/5 min per IP, password change 10/hour per user, plus scan limits | `ratelimit.py`; `test_rate_limit` |
| Uploads | 15 MB limit (`MAX_UPLOAD_MB`). Pillow must decode the file as JPEG, PNG, WebP or BMP (no SVG). 40 MP decompression-bomb cap. Minimum side 32 px. Re-encoded, which strips EXIF and GPS. Content-hash file names, so client file names are never used as paths | `storage.py`; upload tests |
| Input validation | Pydantic schemas with length limits. Species values are checked against the knowledge base | `schemas.py`, `scans.py` |
| Static files | SPA paths are resolved and must stay inside `frontend/dist` (no path traversal). API paths never fall through to the SPA | `main.py` |
| SQL | SQLAlchemy ORM only; no string-built SQL | grep |
| CORS | Explicit origin list from `CORS_ORIGINS`, no credentials. The production UI is same-origin | `main.py` |
| Headers | `nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, and HSTS in production | `main.py` |
| CSV export | Text cells starting with `= + - @` are escaped (formula injection) | `test_csv_cells_are_formula_injection_safe` |
| Errors | An unhandled-exception handler returns a generic 500 (message and exception type, no stack trace) | `main.py` |

## Dependency vulnerabilities
| Scope | Result | Decision |
|---|---|---|
| Python, `backend/requirements.lock.txt` | **No known vulnerabilities** (pip-audit) | — |
| npm, shipped production packages | 2 moderate, both in `react-router` 6 (GHSA-wrjc-x8rr-h8h6 open redirect via `<Link>`/`navigate`; GHSA-337j-9hxr-rhxg SSR hydration) | Accepted for now. The app navigates only to its own route state, never to user-supplied URLs, and it does not use SSR. The fix is a major upgrade to react-router 7, planned as a separate change with the E2E suite. |
| npm, dev tooling only (vitest, tinypool, vite/esbuild dev server) | 1 high and 2 critical (tinypool, via vitest), plus moderates | These are not in the production bundle. They matter only on a developer machine running tests or `npm run dev`. The fixes are major upgrades (vitest 5, vite 8), planned with CI verification. Don't expose the dev server to a network. |

## Open items
* Put the react-router 7 and vite/vitest major upgrades on their own branch, with the full CI suite.
* Data is not persistent on the free Render instance until `DATABASE_URL` points at PostgreSQL. This is an availability issue, not a confidentiality one.
* JWTs are kept in `localStorage`, a common SPA trade-off. The risk is mitigated by the strict headers, by never rendering user-supplied HTML (React escaping, and the Markdown renderer allows only safe links), and by revocable tokens that expire after 12 hours (`JWT_EXPIRE_MINUTES`).
