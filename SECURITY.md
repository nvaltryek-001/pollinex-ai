# Security Policy

## Reporting
Please report vulnerabilities privately to the repository owner (GitHub *Security → Report a vulnerability*). Do not open public issues for security problems.

## Measures in place
* Passwords: PBKDF2-HMAC-SHA256, 600k iterations, per-user salt, constant-time compare; password policy on registration.
* Sessions: HS256 JWT with expiry; `token_version` per user so logout, role change or deactivation revoke all tokens.
  Production refuses to start without `JWT_SECRET`; development uses an ephemeral random secret (never a hard-coded one).
* Authorisation: role dependencies (admin / researcher / user) and per-record ownership checks (404 on foreign IDs).
* Uploads: size limit, decompression-bomb guard (40 MP), format allow-list via content parsing (not extension), EXIF-orientation
  fix and **re-encoding that strips EXIF/GPS**, content-addressed storage, path-traversal guard on file serving.
* Archives in dataset scripts: MD5 verification and zip/tar-slip guards.
* HTTP: CORS allow-list, `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, camera Permissions-Policy.
* Frontend markdown renderer never injects HTML and drops non-http(s) links.
* Secrets only via environment variables; `.env` is git-ignored.

## Known considerations
* Model bundles are loaded with joblib (pickle). Only load model files you produced or trust; `/admin/models/reload` reads
  local files only and requires admin.
* JWTs are stored in `localStorage` for simplicity; deploy with a strict CSP and HTTPS. Moving to HttpOnly cookies is a planned hardening.
* Rate limiting is not built in; put the API behind a reverse proxy with rate limits in public deployments.
