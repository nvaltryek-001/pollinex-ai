"""SQLAlchemy ORM models. Images are stored on disk; rows hold paths + metadata only."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)  # admin | researcher | user
    description: Mapped[str] = mapped_column(String(255), default="")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)  # bump to revoke all tokens (logout)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    role: Mapped[Role] = relationship(lazy="joined")


class Species(Base):
    __tablename__ = "species"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    common_name: Mapped[str] = mapped_column(String(120))
    scientific_name: Mapped[str] = mapped_column(String(160))
    primary_mechanism: Mapped[str] = mapped_column(String(40))
    knowledge: Mapped[dict] = mapped_column(JSON)
    reference_image_count: Mapped[int] = mapped_column(Integer, default=0)


class FieldLocation(Base):
    __tablename__ = "field_locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Plant(Base):
    __tablename__ = "plants"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[int | None] = mapped_column(ForeignKey("field_locations.id", ondelete="SET NULL"), nullable=True, index=True)
    species_id: Mapped[str | None] = mapped_column(ForeignKey("species.id"), nullable=True)
    label: Mapped[str] = mapped_column(String(120))
    cultivar: Mapped[str] = mapped_column(String(120), default="")
    planted_on: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UploadedImage(Base):
    __tablename__ = "uploaded_images"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    storage_path: Mapped[str] = mapped_column(String(400))
    original_name: Mapped[str] = mapped_column(String(255), default="")
    content_type: Mapped[str] = mapped_column(String(40))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EnvironmentRecord(Base):
    __tablename__ = "environment_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[int | None] = mapped_column(ForeignKey("field_locations.id", ondelete="SET NULL"), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    relative_humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    rain_mm_h: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    observation: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(80))  # "manual" | "open-meteo"
    source_detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(80))
    task: Mapped[str] = mapped_column(String(40))  # detection | species | ...
    backend: Mapped[str] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (Index("ix_model_task_version", "task", "version", unique=True),)


class Scan(Base):
    __tablename__ = "scans"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("uploaded_images.id", ondelete="CASCADE"))
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plants.id", ondelete="SET NULL"), nullable=True)
    field_id: Mapped[int | None] = mapped_column(ForeignKey("field_locations.id", ondelete="SET NULL"), nullable=True)
    environment_id: Mapped[int | None] = mapped_column(ForeignKey("environment_records.id", ondelete="SET NULL"), nullable=True)
    model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="upload")  # upload | camera | live
    mode: Mapped[str] = mapped_column(String(16), default="auto")
    species_hint: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="completed")
    detection_method: Mapped[str] = mapped_column(String(32), default="trained_model")
    flower_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    image: Mapped[UploadedImage] = relationship(lazy="joined")
    detections: Mapped[list["FlowerDetection"]] = relationship(back_populates="scan", cascade="all, delete-orphan",
                                                               order_by="FlowerDetection.index")


class FlowerDetection(Base):
    __tablename__ = "flower_detections"
    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), index=True)
    index: Mapped[int] = mapped_column(Integer)
    x1: Mapped[float] = mapped_column(Float)
    y1: Mapped[float] = mapped_column(Float)
    x2: Mapped[float] = mapped_column(Float)
    y2: Mapped[float] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    method: Mapped[str] = mapped_column(String(32))
    species_id: Mapped[str] = mapped_column(String(40), index=True)
    species_confidence: Mapped[float] = mapped_column(Float, default=0)
    species_method: Mapped[str] = mapped_column(String(40))
    pose: Mapped[dict] = mapped_column(JSON, default=dict)
    health: Mapped[dict] = mapped_column(JSON, default=dict)
    scan: Mapped[Scan] = relationship(back_populates="detections")
    structure: Mapped["StructureDetection | None"] = relationship(cascade="all, delete-orphan", uselist=False, lazy="joined")
    maturity: Mapped["MaturityPrediction | None"] = relationship(cascade="all, delete-orphan", uselist=False, lazy="joined")
    readiness: Mapped["ReadinessPrediction | None"] = relationship(cascade="all, delete-orphan", uselist=False, lazy="joined")


class StructureDetection(Base):
    __tablename__ = "structure_detections"
    id: Mapped[int] = mapped_column(primary_key=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("flower_detections.id", ondelete="CASCADE"), unique=True)
    method: Mapped[str] = mapped_column(String(32))
    structure_detection_available: Mapped[bool] = mapped_column(Boolean, default=False)
    yellow_cluster_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class MaturityPrediction(Base):
    __tablename__ = "maturity_predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("flower_detections.id", ondelete="CASCADE"), unique=True)
    stage: Mapped[str] = mapped_column(String(24), index=True)
    score: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(32))
    uncertain: Mapped[bool] = mapped_column(Boolean, default=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class ReadinessPrediction(Base):
    __tablename__ = "readiness_predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("flower_detections.id", ondelete="CASCADE"), unique=True)
    category: Mapped[str] = mapped_column(String(24), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class PollinationRecord(Base):
    """A user-logged pollination action (manual/assisted) - real-world record, not a model output."""
    __tablename__ = "pollination_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plants.id", ondelete="SET NULL"), nullable=True)
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("scans.id", ondelete="SET NULL"), nullable=True)
    species_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    method: Mapped[str] = mapped_column(String(40))  # natural | manual_brush | vibration | ...
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    flowers_treated: Mapped[int] = mapped_column(Integer, default=1)
    outcome_observed: Mapped[str | None] = mapped_column(String(40), nullable=True)  # e.g. fruit_set / no_set / pending
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Simulation(Base):
    __tablename__ = "simulations"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("scans.id", ondelete="SET NULL"), nullable=True)
    species_id: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(16), default="created")  # created | completed | failed
    params: Mapped[dict] = mapped_column(JSON)
    result_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    result_path: Mapped[str | None] = mapped_column(String(400), nullable=True)  # frames stored on disk
    sim_version: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id"), nullable=True)
    task: Mapped[str] = mapped_column(String(40))
    dataset_id: Mapped[str] = mapped_column(String(80))
    split: Mapped[str] = mapped_column(String(20))
    metrics: Mapped[dict] = mapped_column(JSON)
    report_path: Mapped[str] = mapped_column(String(400))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DatasetMetadata(Base):
    __tablename__ = "dataset_metadata"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(400))
    license: Mapped[str] = mapped_column(String(300))
    task_support: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(40))  # integrated | script_only | documented_only | rejected
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class ResearchReference(Base):
    __tablename__ = "research_references"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    title: Mapped[str] = mapped_column(String(400))
    authors: Mapped[str] = mapped_column(String(400))
    year: Mapped[int] = mapped_column(Integer)
    venue: Mapped[str] = mapped_column(String(200))
    doi_or_url: Mapped[str] = mapped_column(String(300))
    evidence_type: Mapped[str] = mapped_column(String(8))
    relevance: Mapped[str] = mapped_column(Text, default="")


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity: Mapped[str] = mapped_column(String(40), default="")
    entity_id: Mapped[str] = mapped_column(String(40), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
