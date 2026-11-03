"""Fields, plants, environmental records and real-world pollination logs."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import EnvironmentRecord, FieldLocation, Plant, PollinationRecord, User
from ..schemas import (EnvironmentIn, EnvironmentOut, FieldIn, FieldOut, Page, PlantIn, PlantOut, PollinationIn,
                       PollinationOut, WeatherFetchIn)
from ..security import get_current_user
from ..services import engine
from ..services.records import log, paginate
from ..services.weather import fetch_current

router = APIRouter(tags=["field management"])


def _owned(db, model, oid, user):
    o = db.get(model, oid)
    if not o or o.owner_id != user.id:
        raise HTTPException(404, f"{model.__name__} not found")
    return o


def _check_refs(db, user, field_id=None, plant_id=None, species_id=None):
    if field_id is not None:
        _owned(db, FieldLocation, field_id, user)
    if plant_id is not None:
        _owned(db, Plant, plant_id, user)
    if species_id and not engine.get_species(species_id):
        raise HTTPException(422, f"unknown species '{species_id}'")


# ----- fields -----
@router.get("/fields", response_model=list[FieldOut])
def list_fields(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(FieldLocation).where(FieldLocation.owner_id == user.id).order_by(FieldLocation.name)).all()


@router.post("/fields", response_model=FieldOut, status_code=201)
def create_field(body: FieldIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = FieldLocation(owner_id=user.id, **body.model_dump())
    db.add(f)
    db.flush()
    log(db, user, "field.create", "field", f.id)
    db.commit()
    return f


@router.put("/fields/{fid}", response_model=FieldOut)
def update_field(fid: int, body: FieldIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = _owned(db, FieldLocation, fid, user)
    for k, v in body.model_dump().items():
        setattr(f, k, v)
    db.commit()
    return f


@router.delete("/fields/{fid}", status_code=204)
def delete_field(fid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, FieldLocation, fid, user))
    db.commit()


# ----- plants (flower inventory) -----
@router.get("/plants", response_model=Page[PlantOut])
def list_plants(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), field_id: int | None = None,
                species_id: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Plant).where(Plant.owner_id == user.id).order_by(Plant.created_at.desc())
    if field_id:
        stmt = stmt.where(Plant.field_id == field_id)
    if species_id:
        stmt = stmt.where(Plant.species_id == species_id)
    items, total = paginate(db, stmt, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/plants", response_model=PlantOut, status_code=201)
def create_plant(body: PlantIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_refs(db, user, field_id=body.field_id, species_id=body.species_id)
    p = Plant(owner_id=user.id, **body.model_dump())
    db.add(p)
    db.flush()
    log(db, user, "plant.create", "plant", p.id)
    db.commit()
    return p


@router.put("/plants/{pid}", response_model=PlantOut)
def update_plant(pid: int, body: PlantIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _owned(db, Plant, pid, user)
    _check_refs(db, user, field_id=body.field_id, species_id=body.species_id)
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    db.commit()
    return p


@router.delete("/plants/{pid}", status_code=204)
def delete_plant(pid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, Plant, pid, user))
    db.commit()


# ----- environment -----
@router.get("/environment", response_model=Page[EnvironmentOut])
def list_env(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), field_id: int | None = None,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(EnvironmentRecord).where(EnvironmentRecord.owner_id == user.id).order_by(EnvironmentRecord.observed_at.desc())
    if field_id:
        stmt = stmt.where(EnvironmentRecord.field_id == field_id)
    items, total = paginate(db, stmt, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/environment", response_model=EnvironmentOut, status_code=201, summary="Manual environmental observation")
def create_env(body: EnvironmentIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_refs(db, user, field_id=body.field_id)
    rec = EnvironmentRecord(owner_id=user.id, source="manual", source_detail={"entered_by": user.email}, **body.model_dump())
    db.add(rec)
    db.flush()
    log(db, user, "environment.manual", "environment", rec.id)
    db.commit()
    return rec


@router.post("/environment/fetch", response_model=EnvironmentOut, status_code=201,
             summary="Fetch current conditions from Open-Meteo (records provider + timestamp)")
def fetch_env(body: WeatherFetchIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_refs(db, user, field_id=body.field_id)
    w = fetch_current(body.latitude, body.longitude)
    rec = EnvironmentRecord(owner_id=user.id, field_id=body.field_id, observed_at=w["observed_at"],
                            temperature_c=w["temperature_c"], relative_humidity_pct=w["relative_humidity_pct"],
                            rain_mm_h=w["rain_mm_h"], wind_kmh=w["wind_kmh"], source="open-meteo",
                            source_detail=w["source_detail"], observation="")
    db.add(rec)
    db.flush()
    log(db, user, "environment.fetch", "environment", rec.id)
    db.commit()
    return rec


@router.get("/environment/{eid}/assessment", summary="Species-specific environmental assessment for a record")
def assess_env(eid: int, species_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rec = _owned(db, EnvironmentRecord, eid, user)
    from ..services.records import env_dict
    r = engine.estimate_readiness(species_id, {"stage": "fully_open", "score": 1.0}, None, None, env_dict(rec))
    return {"species_id": species_id, "factors": r["factors"],
            "note": "Environmental decision support only; does not replace species-specific biological validation."}


@router.delete("/environment/{eid}", status_code=204)
def delete_env(eid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, EnvironmentRecord, eid, user))
    db.commit()


# ----- pollination history (real-world actions logged by the user) -----
@router.get("/pollination-records", response_model=Page[PollinationOut])
def list_poll(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    items, total = paginate(db, select(PollinationRecord).where(PollinationRecord.owner_id == user.id)
                            .order_by(PollinationRecord.performed_at.desc()), page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/pollination-records", response_model=PollinationOut, status_code=201)
def create_poll(body: PollinationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_refs(db, user, plant_id=body.plant_id, species_id=body.species_id)
    r = PollinationRecord(owner_id=user.id, **body.model_dump())
    db.add(r)
    db.flush()
    log(db, user, "pollination.record", "pollination_record", r.id)
    db.commit()
    return r


@router.put("/pollination-records/{rid}", response_model=PollinationOut)
def update_poll(rid: int, body: PollinationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _owned(db, PollinationRecord, rid, user)
    _check_refs(db, user, plant_id=body.plant_id, species_id=body.species_id)
    for k, v in body.model_dump().items():
        setattr(r, k, v)
    db.commit()
    return r
