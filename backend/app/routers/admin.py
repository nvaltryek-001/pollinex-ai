import json
import platform
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..config import REPO_ROOT, get_settings
from ..db import get_db
from ..models import ActivityLog, DatasetMetadata, EvaluationRun, ModelVersion, ResearchReference, Role, User
from ..schemas import Page, UserOut, UserUpdate
from ..security import ROLES, get_current_user, require_roles
from ..services import engine
from ..services.records import log, paginate

router = APIRouter(tags=["administration"])
admin_only = require_roles("admin")
research_roles = require_roles("admin", "researcher")


@router.get("/admin/users", response_model=Page[UserOut])
def users(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), _: User = Depends(admin_only),
          db: Session = Depends(get_db)):
    items, total = paginate(db, select(User).order_by(User.created_at), page, page_size)
    return {"items": [UserOut.of(u) for u in items], "total": total, "page": page, "page_size": page_size}


@router.patch("/admin/users/{uid}", response_model=UserOut)
def update_user(uid: int, body: UserUpdate, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "user not found")
    if body.role is not None:
        if body.role not in ROLES:
            raise HTTPException(422, f"role must be one of {ROLES}")
        if u.id == admin.id and body.role != "admin":
            raise HTTPException(409, "you cannot remove your own admin role")
        u.role_id = db.scalar(select(Role.id).where(Role.name == body.role))
        u.token_version += 1  # force re-login with new role claims
    if body.is_active is not None:
        if u.id == admin.id and not body.is_active:
            raise HTTPException(409, "you cannot deactivate yourself")
        u.is_active = body.is_active
        u.token_version += 1
    if body.full_name is not None:
        u.full_name = body.full_name
    log(db, admin, "admin.user_update", "user", uid, **body.model_dump(exclude_none=True))
    db.commit()
    db.refresh(u)
    return UserOut.of(u)


@router.get("/admin/activity")
def activity(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), _: User = Depends(admin_only),
             db: Session = Depends(get_db)):
    items, total = paginate(db, select(ActivityLog).order_by(ActivityLog.created_at.desc()), page, page_size)
    return {"items": [{"id": a.id, "user_id": a.user_id, "action": a.action, "entity": a.entity, "entity_id": a.entity_id,
                       "details": a.details, "created_at": a.created_at} for a in items],
            "total": total, "page": page, "page_size": page_size}


@router.get("/admin/models")
def models(_: User = Depends(research_roles), db: Session = Depends(get_db)):
    an = engine.get_analyzer()
    return {"active": an.model_info(), "detector_choice": engine.detector_choice(),
            "available_detectors": engine.available_detectors(),
            "registered": [{"id": m.id, "name": m.name, "version": m.version, "task": m.task, "backend": m.backend,
                            "is_active": m.is_active, "registered_at": m.registered_at, "details": m.details}
                           for m in db.scalars(select(ModelVersion).order_by(ModelVersion.registered_at.desc()))],
            "evaluation_runs": [{"id": e.id, "task": e.task, "dataset_id": e.dataset_id, "split": e.split, "metrics": e.metrics,
                                 "report_path": e.report_path, "created_at": e.created_at}
                                for e in db.scalars(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()))]}


@router.post("/admin/models/reload", summary="Reload detector + gallery from disk (after retraining)")
def reload_models(admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    engine.get_analyzer.cache_clear()
    info = engine.get_analyzer().model_info()
    log(db, admin, "admin.models_reload", details=info)
    db.commit()
    return info


class DetectorSwitch(BaseModel):
    detector: str = Field(pattern="^(auto|yolo11|pixel)$")


@router.post("/admin/models/detector", summary="Switch the active flower detector (auto | yolo11 | pixel)")
def set_detector(body: DetectorSwitch, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    try:
        info = engine.switch_detector(body.detector)
    except FileNotFoundError as e:
        raise HTTPException(409, str(e)) from e
    log(db, admin, "admin.detector_switch", details={"detector": body.detector, **info})
    db.commit()
    return {"detector_choice": engine.detector_choice(), "active": info}


@router.get("/datasets", summary="Dataset manifest (verified sources, licences, task support)")
def datasets(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(DatasetMetadata).order_by(DatasetMetadata.status, DatasetMetadata.id)).all()
    report = REPO_ROOT / "datasets" / "reports" / "usda_fruit_flower_report.json"
    return {"datasets": [{"id": d.id, "name": d.name, "url": d.url, "license": d.license, "task_support": d.task_support,
                          "status": d.status, "details": d.details} for d in rows],
            "prepared_report": json.loads(report.read_text()) if report.exists() else None}


@router.get("/research/references")
def references(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [{"id": r.id, "title": r.title, "authors": r.authors, "year": r.year, "venue": r.venue,
             "doi_or_url": r.doi_or_url, "evidence_type": r.evidence_type, "relevance": r.relevance}
            for r in db.scalars(select(ResearchReference).order_by(ResearchReference.year.desc()))]


@router.get("/research/documents/{name}", summary="Research markdown documents shipped with the repo")
def research_doc(name: str, _: User = Depends(get_current_user)):
    allowed = {"literature_review", "research_comparison", "research_gaps", "methodology"}
    if name not in allowed:
        raise HTTPException(404, "document not found")
    return {"name": name, "markdown": (REPO_ROOT / "research" / f"{name}.md").read_text(encoding="utf-8")}


@router.get("/health", tags=["system"], summary="System health (DB, models, storage)")
def health(db: Session = Depends(get_db)):
    checks = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:  # report, don't hide
        checks["database"] = f"error: {type(e).__name__}"
    try:
        info = engine.get_analyzer().model_info()
        checks["models"] = "ok"
    except Exception as e:
        info, checks["models"] = None, f"error: {type(e).__name__}: {e}"
    s = get_settings()
    checks["storage"] = "ok" if s.upload_dir.exists() else "missing"
    status_ = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    dialect = db.get_bind().dialect.name  # e.g. "postgresql" or "sqlite" - never the URL or credentials
    return {"status": status_, "checks": checks, "model": info, "environment": s.environment, "database_backend": dialect,
            "python": platform.python_version(), "time": datetime.now(timezone.utc).isoformat()}
