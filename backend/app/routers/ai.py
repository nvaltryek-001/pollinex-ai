"""Module-level AI endpoints (each runs one stage of the pipeline on an uploaded image)."""
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..db import get_db
from ..models import Species, User
from ..security import get_current_user, require_roles
from ..services import engine
from ..services.records import log
from ..services.storage import decode_image

router = APIRouter(prefix="/ai", tags=["ai"])


async def _rgb(file: UploadFile) -> np.ndarray:
    img, _ = decode_image(await file.read())
    if max(img.size) > 2560:
        img.thumbnail((2560, 2560))
    return np.asarray(img)


@router.post("/detect", summary="Flower detection only (boxes, scores, count)")
async def detect(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    rgb = await _rgb(file)
    an = engine.get_analyzer()
    res = await run_in_threadpool(an.detector.detect, rgb)
    return {"backend": res.backend, "model_version": res.model_version, "latency_ms": round(res.latency_ms, 1),
            "image_size": res.image_size, "flower_count": len(res.detections), "warnings": res.warnings,
            "detections": [d.to_dict() for d in res.detections]}


@router.post("/analyze", summary="Full pipeline without saving (species, stage, structure, health, pose, readiness)")
async def analyze(file: UploadFile = File(...), mode: str = Form("auto"), species_hint: str | None = Form(None),
                  user: User = Depends(get_current_user)):
    if mode not in {"auto", "scene", "closeup"}:
        raise HTTPException(422, "invalid mode")
    if species_hint and not engine.get_species(species_hint):
        raise HTTPException(422, "unknown species")
    rgb = await _rgb(file)
    return await run_in_threadpool(engine.analyze, rgb, mode=mode, species_hint=species_hint)


@router.post("/classify-species", summary="Open-set species classification of a single flower crop")
async def classify(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    rgb = await _rgb(file)
    return {**engine.get_analyzer().gallery.predict(rgb), "method": "trained_reference_gallery",
            "gallery": engine.get_analyzer().gallery.counts()}


@router.post("/structure", summary="Centre-region heuristic for a single flower crop (not anther/stigma detection)")
async def structure(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    from pollinex_ai.structure import analyze_centre, apply_structure_model
    rgb = await _rgb(file)
    out = analyze_centre(rgb)
    sm = engine.get_analyzer().structure_model
    return apply_structure_model(out, rgb, sm) if sm is not None else out


@router.post("/maturity", summary="Developmental-stage heuristic for a single flower crop")
async def maturity(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    from pollinex_ai.maturity import estimate_stage
    return estimate_stage(await _rgb(file))


@router.post("/health", summary="Visible-anomaly indicators for a single flower crop")
async def health(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    from pollinex_ai.health import analyze_health
    return analyze_health(await _rgb(file))


class ReadinessIn(BaseModel):
    species_id: str
    stage: str = Field(pattern=r"^(bud|early_bloom|partially_open|fully_open|senescent)$")
    stage_score: float = Field(default=0.7, ge=0, le=1)
    yellow_cluster_visible: bool = False
    temperature_c: float | None = None
    relative_humidity_pct: float | None = None
    rain_mm_h: float | None = None
    wind_kmh: float | None = None


@router.post("/readiness", summary="Rule-based visual readiness estimate from explicit inputs")
def readiness(body: ReadinessIn, user: User = Depends(get_current_user)):
    env = {k: getattr(body, k) for k in ("temperature_c", "relative_humidity_pct", "rain_mm_h", "wind_kmh")}
    env = {**env, "source": "manual (request body)"} if any(v is not None for v in env.values()) else None
    return engine.estimate_readiness(body.species_id, {"stage": body.stage, "score": body.stage_score},
                                     {"yellow_cluster_visible": body.yellow_cluster_visible}, None, env)


@router.get("/species", summary="Species knowledge base")
def species_list(user: User = Depends(get_current_user)):
    kb = engine.load_kb()
    gallery = engine.get_analyzer().gallery.counts()
    status = engine.get_analyzer().gallery.meta.get("species_status", {})
    return {"version": kb["version"], "disclaimer": kb["disclaimer"], "evidence_sources": kb["evidence_sources"],
            "botany_scope": kb.get("botany_scope"), "fruit_recognition": kb.get("fruit_recognition"),
            "species": [{**s, "reference_images": gallery.get(s["id"], 0),
                         "ai_support": status.get(s["id"], "not_supported" if status else "not_evaluated")} for s in kb["species"]],
            "gallery_threshold": engine.get_analyzer().gallery.threshold}


@router.post("/species/{species_id}/references", summary="Add a reference image to the species gallery (researcher/admin)")
async def add_reference(species_id: str, file: UploadFile = File(...),
                        user: User = Depends(require_roles("admin", "researcher")), db: Session = Depends(get_db)):
    if not engine.get_species(species_id):
        raise HTTPException(404, "species not in knowledge base")
    rgb = await _rgb(file)
    counts = await run_in_threadpool(engine.add_reference, species_id, rgb, f"user:{user.id}:{file.filename}")
    sp = db.get(Species, species_id)
    if sp:
        sp.reference_image_count = counts.get(species_id, 0)
    log(db, user, "species.add_reference", "species", species_id)
    db.commit()
    return {"species_id": species_id, "gallery_counts": counts,
            "note": "Reference added. Accuracy for this species has NOT been evaluated until a held-out test set exists."}
