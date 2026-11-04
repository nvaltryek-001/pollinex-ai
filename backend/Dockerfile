# Build from the repository root:  docker build -f backend/Dockerfile -t pollinex-backend .
# Stage 1: build the React app (served by the API itself in single-service deployments, e.g. Render free plan)
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV VITE_API_URL=""
RUN npx vite build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 curl && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 pollinex
WORKDIR /srv/pollinex

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY ai-engine ai-engine
COPY simulation simulation
COPY research research
COPY datasets/dataset_sources.json datasets/dataset_sources.json
COPY datasets/reports datasets/reports
COPY backend backend
COPY --from=web /web/dist frontend/dist
RUN mkdir -p backend/storage && chown -R pollinex:pollinex backend/storage

USER pollinex
WORKDIR /srv/pollinex/backend
ENV AUTO_CREATE_TABLES=false
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD curl -fsS http://localhost:${PORT:-8000}/api/v1/health || exit 1
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --proxy-headers"]
