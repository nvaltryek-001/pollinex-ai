# Build from the repository root:  docker build -f backend/Dockerfile -t pollinex-backend .
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
RUN mkdir -p backend/storage && chown -R pollinex:pollinex backend/storage

USER pollinex
WORKDIR /srv/pollinex/backend
ENV AUTO_CREATE_TABLES=false
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD curl -fsS http://localhost:8000/api/v1/health || exit 1
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-1} --proxy-headers"]
