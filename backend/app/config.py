"""Runtime configuration from environment variables (see .env.example)."""
from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    """Minimal .env loader (no extra dependency): KEY=VALUE lines, '#' comments, optional quotes.
    Real environment variables always win, so Docker/CI/hosting settings are never overridden."""
    if os.environ.get("POLLINEX_SKIP_DOTENV") == "1" or not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():  # utf-8-sig: tolerate BOM from PowerShell 5.1
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and val and key not in os.environ:
            os.environ[key] = val


load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


class Settings(BaseModel):
    app_name: str = "POLLINEX AI"
    environment: str = Field(default_factory=lambda: _env("POLLINEX_ENV", "development"))
    database_url: str = Field(default_factory=lambda: _env("DATABASE_URL", f"sqlite:///{REPO_ROOT / 'backend' / 'pollinex.db'}"))
    jwt_secret: str = Field(default_factory=lambda: _env("JWT_SECRET") or "")
    jwt_minutes: int = Field(default_factory=lambda: int(_env("JWT_EXPIRE_MINUTES", "720")))
    upload_dir: Path = Field(default_factory=lambda: Path(_env("UPLOAD_DIR", str(REPO_ROOT / "backend" / "storage" / "uploads"))))
    gallery_dir: Path = Field(default_factory=lambda: Path(_env("GALLERY_DIR", str(REPO_ROOT / "backend" / "storage" / "gallery"))))
    max_upload_mb: int = Field(default_factory=lambda: int(_env("MAX_UPLOAD_MB", "15")))
    cors_origins: list[str] = Field(default_factory=lambda: [o.strip() for o in (_env("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173") or "").split(",") if o.strip()])
    weather_enabled: bool = Field(default_factory=lambda: (_env("WEATHER_API_ENABLED", "true") or "").lower() == "true")
    weather_base_url: str = Field(default_factory=lambda: _env("WEATHER_API_URL", "https://api.open-meteo.com/v1/forecast"))
    admin_email: str | None = Field(default_factory=lambda: _env("BOOTSTRAP_ADMIN_EMAIL"))
    admin_password: str | None = Field(default_factory=lambda: _env("BOOTSTRAP_ADMIN_PASSWORD"))
    inference_workers: int = Field(default_factory=lambda: int(_env("INFERENCE_WORKERS", "1")))

    def ensure(self) -> "Settings":
        # hosting providers (Render, Heroku) hand out postgres:// or postgresql:// URLs; the installed driver is psycopg 3
        for prefix in ("postgres://", "postgresql://"):
            if self.database_url.startswith(prefix):
                self.database_url = "postgresql+psycopg://" + self.database_url[len(prefix):]
        if self.jwt_secret.startswith("CHANGE_ME"):
            if self.environment == "production":
                raise RuntimeError("JWT_SECRET still has the .env.example placeholder value")
            self.jwt_secret = ""
        if not self.jwt_secret:
            if self.environment == "production":
                raise RuntimeError("JWT_SECRET must be set in production")
            # development: ephemeral secret (tokens invalidate on restart) - never a hard-coded default
            self.jwt_secret = secrets.token_urlsafe(48)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.gallery_dir.mkdir(parents=True, exist_ok=True)
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings().ensure()
