import json
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionLocal, get_db
from ..models import Scan, Simulation, User
from ..schemas import Page, SimulationIn, SimulationOut, SweepIn
from ..security import get_current_user
from ..services import engine
from ..services.records import log, paginate

router = APIRouter(prefix="/simulations", tags=["simulation"])
DISCLAIMER = "Computational simulation only - not evidence of fertilisation, fruit set or yield."


def _sim_dir():
    d = get_settings().upload_dir.parent / "simulations"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _params(species_id: str, overrides: dict):
    sp = engine.get_species(species_id)
    if not sp:
        raise HTTPException(404, f"species '{species_id}' not in knowledge base")
    try:
        return engine.SimParams.from_profile(sp["id"], sp["simulation_profile"], overrides)
    except (ValueError, TypeError) as e:
        raise HTTPException(422, str(e))


def _owned(db, sim_id, user) -> Simulation:
    s = db.get(Simulation, sim_id)
    if not s or s.owner_id != user.id:
        raise HTTPException(404, "simulation not found")
    return s


def _execute(sim_id: int) -> None:
    db = SessionLocal()
    try:
        sim = db.get(Simulation, sim_id)
        p = engine.SimParams(**{**sim.params, "effector_offset_mm": tuple(sim.params.get("effector_offset_mm", (0, 0)))})
        try:
            res = engine.run_simulation(p)
        except Exception as e:  # recorded, not swallowed
            sim.status, sim.result_summary = "failed", {"error": f"{type(e).__name__}: {e}"}
            db.commit()
            return
        path = _sim_dir() / f"sim_{sim.id}.json"
        path.write_text(json.dumps({"frames": res["frames"], "geometry": res["geometry"]}))
        sim.result_path = str(path)
        sim.result_summary = {k: v for k, v in res.items() if k not in ("frames", "geometry", "params")}
        sim.sim_version = res["sim_version"]
        sim.status, sim.completed_at = "completed", datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


@router.post("", response_model=SimulationOut, status_code=201, summary="Create a simulation (not yet executed)")
def create(body: SimulationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _params(body.species_id, body.overrides)
    if body.scan_id:
        scan = db.get(Scan, body.scan_id)
        if not scan or scan.owner_id != user.id:
            raise HTTPException(404, "scan not found")
    from dataclasses import asdict
    params = {**asdict(p), "effector_offset_mm": list(p.effector_offset_mm)}
    sim = Simulation(owner_id=user.id, scan_id=body.scan_id, species_id=p.species, params=params, status="created")
    db.add(sim)
    db.flush()
    log(db, user, "simulation.create", "simulation", sim.id)
    db.commit()
    return sim


@router.post("/{sim_id}/execute", response_model=SimulationOut, summary="Execute a created simulation")
def execute(sim_id: int, background: BackgroundTasks, run_async: bool = Query(False), user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    sim = _owned(db, sim_id, user)
    if sim.status == "completed":
        return sim
    if run_async:
        sim.status = "running"
        db.commit()
        background.add_task(_execute, sim.id)
        return sim
    _execute(sim.id)
    db.expire_all()
    return _owned(db, sim_id, user)


@router.get("", response_model=Page[SimulationOut])
def list_sims(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    items, total = paginate(db, select(Simulation).where(Simulation.owner_id == user.id).order_by(Simulation.created_at.desc()),
                            page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{sim_id}", response_model=SimulationOut)
def get_sim(sim_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _owned(db, sim_id, user)


@router.get("/{sim_id}/replay", summary="Recorded particle frames + geometry for client-side replay")
def replay(sim_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sim = _owned(db, sim_id, user)
    if sim.status != "completed" or not sim.result_path:
        raise HTTPException(409, f"simulation is {sim.status}")
    data = json.loads(open(sim.result_path).read())
    return {"id": sim.id, "species_id": sim.species_id, "params": sim.params, "summary": sim.result_summary,
            "disclaimer": DISCLAIMER, **data}


@router.post("/sweep", summary="Parameter sweep (no persistence) for sensitivity analysis")
def sweep(body: SweepIn, user: User = Depends(get_current_user)):
    allowed = {"vibration_hz", "wind_kmh", "effector_offset_mm", "pollen_release_rate", "humidity_pct", "particle_count"}
    if body.parameter not in allowed:
        raise HTTPException(422, f"parameter must be one of {sorted(allowed)}")
    p = _params(body.species_id, body.overrides)
    try:
        rows = engine.parameter_sweep(p, body.parameter, body.values)
    except (ValueError, TypeError) as e:
        raise HTTPException(422, str(e))
    return {"species_id": body.species_id, "parameter": body.parameter, "rows": rows, "disclaimer": DISCLAIMER}
