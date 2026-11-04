"""POLLINEX AI API - FastAPI application factory."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import REPO_ROOT, get_settings
from .db import Base, SessionLocal, engine
from .routers import admin, ai, analytics, auth, records, scans, simulations
from .services.seed import seed

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("pollinex")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if os.environ.get("AUTO_CREATE_TABLES", "true").lower() == "true":
        # Development convenience. Production/Docker uses `alembic upgrade head` (AUTO_CREATE_TABLES=false).
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    if os.environ.get("PRELOAD_MODELS", "true").lower() == "true":
        from .services.engine import get_analyzer
        try:
            get_analyzer()
        except Exception as e:  # surfaced via /health instead of crashing startup
            log.error("model preload failed: %s", e)
    log.info("POLLINEX AI API ready (%s)", settings.environment)
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="POLLINEX AI API",
        version="1.0.0",
        description=("Multi-species flower detection, open-set species recognition, heuristic stage/structure/health "
                     "analysis, rule-based visual pollination-readiness estimation and virtual pollination simulation.\n\n"
                     "Every response states its method (trained_model, heuristic, rule_engine, simulation)."),
        lifespan=lifespan,
    )
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=False,
                       allow_methods=["*"], allow_headers=["Authorization", "Content-Type"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        if s.environment == "production":  # production is served over HTTPS only (Render)
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return resp

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse({"detail": "Internal server error", "error_type": type(exc).__name__}, status_code=500)

    for r in (auth.router, scans.router, ai.router, simulations.router, records.router, analytics.router, admin.router):
        app.include_router(r, prefix="/api/v1")

    dist = Path(os.environ.get("FRONTEND_DIST", str(REPO_ROOT / "frontend" / "dist")))
    if (dist / "index.html").exists():  # single-service deployment: the API also serves the built React app
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles

        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith(("api/", "docs", "redoc", "openapi.json")):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            f = (dist / path).resolve()
            if path and f.is_file() and dist.resolve() in f.parents:
                return FileResponse(f)
            return FileResponse(dist / "index.html", headers={"Permissions-Policy": "camera=(self), geolocation=(self)"})
    else:
        @app.get("/", include_in_schema=False)
        def root():
            return {"name": "POLLINEX AI API", "docs": "/docs", "health": "/api/v1/health"}

    return app


app = create_app()
