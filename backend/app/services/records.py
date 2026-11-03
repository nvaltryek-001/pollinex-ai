"""Persistence + serialisation helpers shared by routers."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (ActivityLog, EnvironmentRecord, FlowerDetection, MaturityPrediction, ModelVersion,
                      ReadinessPrediction, Scan, StructureDetection, UploadedImage, User)
from .storage import StoredImage


def log(db: Session, user: User | None, action: str, entity: str = "", entity_id: Any = "", **details) -> None:
    db.add(ActivityLog(user_id=user.id if user else None, action=action, entity=entity, entity_id=str(entity_id), details=details))


def paginate(db: Session, stmt, page: int, page_size: int):
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return items, total


def env_dict(rec: EnvironmentRecord | None) -> dict | None:
    if not rec:
        return None
    return {"temperature_c": rec.temperature_c, "relative_humidity_pct": rec.relative_humidity_pct,
            "rain_mm_h": rec.rain_mm_h, "wind_kmh": rec.wind_kmh, "source": rec.source,
            "observed_at": rec.observed_at.isoformat() if rec.observed_at else None}


def ensure_model_version(db: Session, info: dict) -> ModelVersion:
    mv = db.scalar(select(ModelVersion).where(ModelVersion.task == "detection", ModelVersion.version == info["detector_version"]))
    if not mv:
        mv = ModelVersion(name="flower-detector", version=info["detector_version"], task="detection",
                          backend=info["detector_backend"], details={"gallery_species": info.get("gallery_species")})
        db.add(mv)
        db.flush()
    return mv


def persist_scan(db: Session, user: User, stored: StoredImage, result: dict, *, source: str, mode: str,
                 species_hint: str | None, plant_id: int | None, field_id: int | None,
                 env: EnvironmentRecord | None, original_name: str = "") -> Scan:
    img = db.scalar(select(UploadedImage).where(UploadedImage.sha256 == stored.sha256, UploadedImage.owner_id == user.id))
    if not img:
        img = UploadedImage(owner_id=user.id, storage_path=stored.rel_path, original_name=original_name[:255],
                            content_type=stored.content_type, width=stored.width, height=stored.height,
                            size_bytes=stored.size_bytes, sha256=stored.sha256)
        db.add(img)
        db.flush()
    mv = ensure_model_version(db, result["model"])
    stage_counts: dict[str, int] = {}
    ready_counts: dict[str, int] = {}
    for f in result["flowers"]:
        if "stage" in f:
            stage_counts[f["stage"]["stage"]] = stage_counts.get(f["stage"]["stage"], 0) + 1
            ready_counts[f["readiness"]["category"]] = ready_counts.get(f["readiness"]["category"], 0) + 1
    scan = Scan(owner_id=user.id, image_id=img.id, plant_id=plant_id, field_id=field_id,
                environment_id=env.id if env else None, model_version_id=mv.id, source=source, mode=mode,
                species_hint=species_hint, detection_method=result["detection_method"],
                flower_count=result["flower_count"], latency_ms=result["latency_ms"], warnings=result["warnings"],
                summary={"species_counts": result["species_counts"], "stage_counts": stage_counts,
                         "readiness_counts": ready_counts, "low_confidence_count": result["low_confidence_count"],
                         "analysed_flowers": len(result["flowers"]), "model": result["model"]})
    db.add(scan)
    db.flush()
    for f in result["flowers"]:
        d = f["detection"]
        fd = FlowerDetection(scan_id=scan.id, index=f["id"], x1=d["box"][0], y1=d["box"][1], x2=d["box"][2], y2=d["box"][3],
                             score=d["score"], low_confidence=d["low_confidence"], method=d["method"],
                             species_id=f["species"]["species"], species_confidence=float(f["species"].get("confidence") or 0),
                             species_method=f["species"]["method"], pose=f.get("pose", {}), health=f.get("health", {}))
        db.add(fd)
        db.flush()
        if "stage" in f:
            db.add(MaturityPrediction(detection_id=fd.id, stage=f["stage"]["stage"], score=f["stage"]["score"],
                                      method=f["stage"]["method"], uncertain=f["stage"]["uncertain"], data=f["stage"]))
            db.add(StructureDetection(detection_id=fd.id, method=f["structure"]["method"],
                                      structure_detection_available=f["structure"]["structure_detection_available"],
                                      yellow_cluster_visible=f["structure"]["yellow_cluster_visible"], data=f["structure"]))
            db.add(ReadinessPrediction(detection_id=fd.id, category=f["readiness"]["category"],
                                       confidence=f["readiness"]["confidence"], data=f["readiness"]))
    log(db, user, "scan.create", "scan", scan.id, flowers=scan.flower_count, source=source)
    db.commit()
    db.refresh(scan)
    return scan


def flower_dict(fd: FlowerDetection) -> dict:
    out = {"id": fd.index, "detection": {"box": [fd.x1, fd.y1, fd.x2, fd.y2], "score": fd.score,
                                         "low_confidence": fd.low_confidence, "method": fd.method},
           "species": {"species": fd.species_id, "confidence": fd.species_confidence, "method": fd.species_method},
           "pose": fd.pose, "health": fd.health}
    if fd.maturity:
        out["stage"] = fd.maturity.data
    if fd.structure:
        out["structure"] = fd.structure.data
    if fd.readiness:
        out["readiness"] = fd.readiness.data
    return out


def scan_dict(scan: Scan, with_flowers: bool = False) -> dict:
    d = {"id": scan.id, "created_at": scan.created_at, "source": scan.source, "mode": scan.mode, "status": scan.status,
         "detection_method": scan.detection_method, "flower_count": scan.flower_count, "latency_ms": scan.latency_ms,
         "warnings": scan.warnings, "summary": scan.summary, "image_url": f"/api/v1/scans/{scan.id}/image",
         "image_width": scan.image.width, "image_height": scan.image.height, "plant_id": scan.plant_id,
         "field_id": scan.field_id, "environment_id": scan.environment_id}
    if with_flowers:
        d["flowers"] = [flower_dict(f) for f in scan.detections]
    return d
