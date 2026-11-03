import asyncio
import base64
import binascii
import json

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect,
                     status)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..db import SessionLocal, get_db
from ..models import EnvironmentRecord, FieldLocation, Plant, Scan, User
from ..schemas import Page, ScanDetail, ScanOut
from ..security import get_current_user, user_from_token
from ..services import engine
from ..services.ratelimit import limit
from ..services.records import env_dict, log, paginate, persist_scan, scan_dict
from ..services.storage import decode_image, resolve_upload, store_image

router = APIRouter(prefix="/scans", tags=["scanning"])
MODES = {"auto", "scene", "closeup"}


def _owned(db: Session, model, obj_id: int | None, user: User):
    if obj_id is None:
        return None
    obj = db.get(model, obj_id)
    if not obj or obj.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} {obj_id} not found")
    return obj


def _check_species(species_hint: str | None) -> str | None:
    if not species_hint:
        return None
    sp = engine.get_species(species_hint)
    if not sp:
        raise HTTPException(422, f"Unknown species '{species_hint}'")
    return sp["id"]


@router.post("", response_model=ScanDetail, status_code=201, summary="Upload an image and analyse it")
async def create_scan(file: UploadFile = File(...), mode: str = Form("auto"), source: str = Form("upload"),
                      species_hint: str | None = Form(None), plant_id: int | None = Form(None),
                      field_id: int | None = Form(None), environment_id: int | None = Form(None),
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    limit(f"scan:{user.id}", 30, 60)
    if mode not in MODES:
        raise HTTPException(422, f"mode must be one of {sorted(MODES)}")
    if source not in {"upload", "camera", "live"}:
        raise HTTPException(422, "source must be upload, camera or live")
    hint = _check_species(species_hint)
    _owned(db, Plant, plant_id, user)
    _owned(db, FieldLocation, field_id, user)
    env = _owned(db, EnvironmentRecord, environment_id, user)
    data = await file.read()
    stored = await run_in_threadpool(store_image, data)
    try:
        result = await run_in_threadpool(engine.analyze, stored.rgb, mode=mode, species_hint=hint, env=env_dict(env))
    except ValueError as e:
        raise HTTPException(422, str(e))
    scan = persist_scan(db, user, stored, result, source=source, mode=mode, species_hint=hint, plant_id=plant_id,
                        field_id=field_id, env=env, original_name=file.filename or "")
    return scan_dict(scan, with_flowers=True)


@router.get("", response_model=Page[ScanOut], summary="Scan history (paginated)")
def list_scans(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), source: str | None = None,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Scan).where(Scan.owner_id == user.id).order_by(Scan.created_at.desc())
    if source:
        stmt = stmt.where(Scan.source == source)
    items, total = paginate(db, stmt, page, page_size)
    return {"items": [scan_dict(s) for s in items], "total": total, "page": page, "page_size": page_size}


@router.get("/{scan_id}", response_model=ScanDetail)
def get_scan(scan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return scan_dict(_owned(db, Scan, scan_id, user), with_flowers=True)


@router.get("/{scan_id}/image", response_class=FileResponse)
def scan_image(scan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    scan = _owned(db, Scan, scan_id, user)
    return FileResponse(resolve_upload(scan.image.storage_path), media_type="image/jpeg")


@router.delete("/{scan_id}", status_code=204)
def delete_scan(scan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    scan = _owned(db, Scan, scan_id, user)
    db.delete(scan)
    log(db, user, "scan.delete", "scan", scan_id)
    db.commit()


class SpeciesCorrection(BaseModel):
    species_id: str = Field(min_length=1, max_length=40, description="knowledge-base species id, or 'unknown'")


@router.patch("/{scan_id}/flowers/{index}/species", summary="Manually correct the species of one detected flower")
def correct_species(scan_id: int, index: int, body: SpeciesCorrection, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Stores the correction (keeping the model's original prediction) and re-runs the species-specific readiness
    rules with the corrected species. The correction is labelled ``user_corrected`` everywhere."""
    scan = _owned(db, Scan, scan_id, user)
    fd = next((f for f in scan.detections if f.index == index), None)
    if fd is None:
        raise HTTPException(404, f"flower {index} not found in scan {scan_id}")
    new_id = "unknown" if body.species_id == "unknown" else _check_species(body.species_id)
    if fd.species_original is None:
        fd.species_original = fd.species_id
        fd.species_original_confidence = fd.species_confidence
    fd.species_id, fd.species_confidence, fd.species_method = new_id, 1.0, "user_corrected"
    if fd.maturity:
        env = db.get(EnvironmentRecord, scan.environment_id) if scan.environment_id else None
        r = engine.estimate_readiness(new_id, fd.maturity.data, fd.structure.data if fd.structure else None, fd.health,
                                      env_dict(env), detection_score=fd.score if fd.method == "trained_model" else 0.6,
                                      species_confidence=1.0 if new_id != "unknown" else 0.0)
        if fd.readiness:
            fd.readiness.category, fd.readiness.confidence, fd.readiness.data = r["category"], r["confidence"], r
    counts: dict[str, int] = {}
    for f in scan.detections:
        counts[f.species_id] = counts.get(f.species_id, 0) + 1
    scan.summary = {**scan.summary, "species_counts": counts,
                    "readiness_counts": _count(f.readiness.category for f in scan.detections if f.readiness)}
    log(db, user, "scan.species_correction", "scan", scan_id, flower=index, to=new_id, original=fd.species_original)
    db.commit()
    db.expire_all()
    return scan_dict(_owned(db, Scan, scan_id, user), with_flowers=True)


def _count(items) -> dict[str, int]:
    out: dict[str, int] = {}
    for x in items:
        out[x] = out.get(x, 0) + 1
    return out


@router.post("/live/frame", summary="Live-frame inference without persisting (frame sampling done client-side)")
async def live_frame(file: UploadFile = File(...), species_hint: str | None = Form(None),
                     user: User = Depends(get_current_user)):
    limit(f"live:{user.id}", 120, 60)
    img, _ = decode_image(await file.read())
    import numpy as np
    rgb = np.asarray(img)
    if max(rgb.shape[:2]) > 1280:
        img.thumbnail((1280, 1280))
        rgb = np.asarray(img)
    result = await run_in_threadpool(engine.analyze, rgb, mode="scene", species_hint=_check_species(species_hint),
                                     detail=False, fast=True)
    return _live_payload(result)


def _live_payload(result: dict) -> dict:
    return {"image_size": result["image_size"], "flower_count": result["flower_count"],
            "detections": [{"box": f["detection"]["box"], "score": f["detection"]["score"],
                            "low_confidence": f["detection"]["low_confidence"], "species": f["species"]["species"],
                            "species_confidence": f["species"].get("confidence")} for f in result["flowers"]],
            "latency_ms": result["latency_ms"], "warnings": result["warnings"], "model": result["model"]}


@router.websocket("/live/ws")
async def live_ws(ws: WebSocket):
    """Protocol: first message {"token": "..."}; then JSON {"image": "<base64 jpeg>"} per sampled frame.
    The server answers each frame; if a frame arrives while one is processing, the client should wait (back-pressure)."""
    await ws.accept()
    db = SessionLocal()
    try:
        hello = json.loads(await asyncio.wait_for(ws.receive_text(), timeout=10))
        try:
            user = user_from_token(hello.get("token", ""), db)
        except HTTPException:
            await ws.close(code=4401)
            return
        await ws.send_json({"type": "ready", "user": user.email})
        while True:
            msg = json.loads(await ws.receive_text())
            try:
                raw = base64.b64decode(msg.get("image", ""), validate=True)
                img, _ = decode_image(raw)
                import numpy as np
                img.thumbnail((1280, 1280))
                result = await run_in_threadpool(engine.analyze, np.asarray(img), mode="scene", detail=False, fast=True)
                await ws.send_json({"type": "result", "frame_id": msg.get("frame_id"), **_live_payload(result)})
            except (HTTPException, binascii.Error, ValueError) as e:
                await ws.send_json({"type": "error", "frame_id": msg.get("frame_id"),
                                    "detail": getattr(e, "detail", str(e))})
    except (WebSocketDisconnect, asyncio.TimeoutError, json.JSONDecodeError):
        pass
    finally:
        db.close()
