# Deployment Guide

> No public deployment has been performed (no hosting credentials). The Docker images and the Compose stack **are built and
> smoke-tested in CI** (API health ok, web served, `/api` proxied). Record public URLs in the README once deployed.

## Docker Compose (single host)
```bash
cp .env.example .env        # set POSTGRES_PASSWORD, JWT_SECRET, CORS_ORIGINS
docker compose up --build -d
docker compose logs -f backend
```
* `db` (PostgreSQL 16, volume `pgdata`), `backend` (runs `alembic upgrade head`, then uvicorn; volume `storage` for uploads),
  `frontend` (nginx serving the build and proxying `/api` incl. WebSockets).
* Put a TLS terminator (Caddy, Traefik, nginx + certbot) in front of port 8080 — HTTPS is required for phone cameras.

## Live deployment (2026-11-04): Render, single service
* **Service:** `pollinex-api` (Docker, free plan, Singapore) at **https://pollinex-api.onrender.com**.
  * `backend/Dockerfile` builds the React app in a Node stage. FastAPI then serves `frontend/dist` with an SPA fallback, so UI and API share one origin and no CORS setup is needed.
  * `/api/v1/*` is the API, `/docs` is OpenAPI, and every other path returns the app.
* **Environment:** `POLLINEX_ENV=production`, a generated `JWT_SECRET`, `AUTO_CREATE_TABLES=false` (Alembic runs at start), and `WEB_CONCURRENCY=1`.
  * `DATABASE_URL` currently points at SQLite inside the container, which is **not persistent**.
* **Persistence:** the database `pollinex-db` (free PostgreSQL, Singapore, expires 2026-12-04) has been created.
  1. In the Render dashboard, copy its **Internal Database URL**.
  2. Set it as the service's `DATABASE_URL`. A `postgres://…` URL is converted to `postgresql+psycopg://` automatically.
  3. Redeploy.
* **Auto-deploy:** the service is set to `autoDeploy: yes` (on commit, branch `main`), but pushes made so far did not start a
  deploy. This happens when Render's GitHub app cannot see the repository. To fix it:
  1. Go to GitHub → *Settings → Applications → Installed GitHub Apps → Render → Configure*.
  2. Under *Repository access*, add `nvaltryek-001/pollinex-ai` and save.
  3. Push a commit and check *Events* on the service.

  Alternatively, go to Render → service → *Settings → Deploy Hook*, copy the URL, add it to GitHub as the repository
  secret `RENDER_DEPLOY_HOOK`, and add a workflow step `curl -fsS -X POST "$RENDER_DEPLOY_HOOK"`. Never commit the hook URL.
  Until then, use **Manual Deploy → Deploy latest commit**.
* **Verifying persistence after setting `DATABASE_URL`:**
  1. Register an account and make a scan.
  2. Use *Manual Deploy → Restart service*.
  3. Log in again and check that the scan is in history.
  4. `GET /api/v1/health` should report a `postgresql` database.
* **First account becomes admin.** Register right after a fresh database is created.

## Vercel status
Project creation through the connected Vercel account returned **HTTP 403** (both `create_project` and
`create_git_project`), and the team has no projects. The Render service already serves the UI, so Vercel is optional. To
use it anyway:
1. Sign in at vercel.com with an account that owns the team.
2. Choose *Add New → Project*, import `nvaltryek-001/pollinex-ai`, set Root Directory `frontend` and env
   `VITE_API_URL=https://pollinex-api.onrender.com`.
3. On Render, add the resulting `https://<project>.vercel.app` to `CORS_ORIGINS`.

## Render (API) + Vercel (web)
1. Render → *New Blueprint* → select the repo → `deployment/render.yaml` (creates the API service and PostgreSQL on free plans; no disk on the free plan).
   Set `CORS_ORIGINS` to the Vercel URL.
2. Vercel → import `frontend/` → env `VITE_API_URL=https://<render-service>.onrender.com`. `vercel.json` handles SPA routing and
   the camera permissions policy.
3. Check `https://<api>/api/v1/health` and register the admin account immediately.

## Production checklist
- [ ] `POLLINEX_ENV=production` (refuses to start without `JWT_SECRET`)
- [ ] strong `JWT_SECRET`, DB password; `.env` not committed
- [ ] HTTPS everywhere; `CORS_ORIGINS` limited to the web origin
- [ ] persistent volume for `storage/` and regular DB backups
- [ ] `WEB_CONCURRENCY` sized to RAM (each worker loads the models, ~300 MB)
- [ ] if you deploy a YOLO11 model, review AGPL-3.0 obligations
