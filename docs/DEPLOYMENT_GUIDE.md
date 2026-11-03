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

## Render (API) + Vercel (web)
1. Render → *New Blueprint* → select the repo → `deployment/render.yaml` (creates the API service, a 1 GB disk and PostgreSQL).
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
