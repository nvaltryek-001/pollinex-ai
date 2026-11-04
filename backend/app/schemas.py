from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# ---------- auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(default="", max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    full_name: str = Field(max_length=120)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    @classmethod
    def of(cls, u) -> "UserOut":
        return cls(id=u.id, email=u.email, full_name=u.full_name, role=u.role.name, is_active=u.is_active, created_at=u.created_at)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut


class UserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    full_name: str | None = Field(default=None, max_length=120)


# ---------- fields / plants ----------
class FieldIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    area_m2: float | None = Field(default=None, ge=0)
    notes: str = Field(default="", max_length=2000)


class FieldOut(FieldIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class PlantIn(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    field_id: int | None = None
    species_id: str | None = None
    cultivar: str = Field(default="", max_length=120)
    planted_on: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    notes: str = Field(default="", max_length=2000)


class PlantOut(PlantIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# ---------- environment ----------
class EnvironmentIn(BaseModel):
    observed_at: datetime
    field_id: int | None = None
    temperature_c: float | None = Field(default=None, ge=-40, le=60)
    relative_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    rain_mm_h: float | None = Field(default=None, ge=0, le=300)
    wind_kmh: float | None = Field(default=None, ge=0, le=250)
    observation: str = Field(default="", max_length=2000)


class EnvironmentOut(EnvironmentIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    source_detail: dict
    created_at: datetime


class WeatherFetchIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    field_id: int | None = None


# ---------- scans ----------
class ScanOut(BaseModel):
    id: int
    created_at: datetime
    source: str
    mode: str
    status: str
    detection_method: str
    flower_count: int
    latency_ms: float
    warnings: list
    summary: dict
    image_url: str
    image_width: int
    image_height: int
    plant_id: int | None
    field_id: int | None
    environment_id: int | None


class ScanDetail(ScanOut):
    flowers: list[dict[str, Any]]


# ---------- simulations ----------
class SimulationIn(BaseModel):
    species_id: str
    scan_id: int | None = None
    overrides: dict[str, Any] = Field(default_factory=dict)

    @field_validator("overrides")
    @classmethod
    def only_known(cls, v: dict) -> dict:
        allowed = {"particle_count", "duration_s", "vibration_hz", "pollen_release_rate", "anther_to_stigma_mm",
                   "stigma_radius_mm", "effector_offset_mm", "wind_kmh", "wind_dir_deg", "humidity_pct", "seed",
                   "target_spread"}
        bad = set(v) - allowed
        if bad:
            raise ValueError(f"unsupported override(s): {sorted(bad)}")
        return v


class SimulationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    species_id: str
    status: str
    params: dict
    result_summary: dict
    sim_version: str
    created_at: datetime
    completed_at: datetime | None
    scan_id: int | None


class SweepIn(BaseModel):
    species_id: str
    parameter: str
    values: list[Any] = Field(min_length=1, max_length=12)
    overrides: dict[str, Any] = Field(default_factory=dict)


# ---------- pollination records ----------
class PollinationIn(BaseModel):
    method: str = Field(pattern=r"^(natural|manual_brush|vibration|air_assisted|cross_pollen_transfer|other)$")
    performed_at: datetime
    species_id: str | None = None
    plant_id: int | None = None
    scan_id: int | None = None
    flowers_treated: int = Field(default=1, ge=1, le=100000)
    outcome_observed: str | None = Field(default=None, pattern=r"^(pending|fruit_set|no_set|partial|unknown)$")
    notes: str = Field(default="", max_length=2000)


class PollinationOut(PollinationIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
