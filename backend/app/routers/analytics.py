import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import REPO_ROOT
from ..db import get_db
from ..models import (EnvironmentRecord, FlowerDetection, MaturityPrediction, PollinationRecord, ReadinessPrediction,
                      Scan, Simulation, User)
from ..security import get_current_user
from ..services.records import log, scan_dict
from ..services.reports import scans_csv, summary_pdf

router = APIRouter(tags=["analytics"])
REPORTS_DIR = REPO_ROOT / "ai-engine" / "reports"


def _scope(user: User, scope: str):
    if scope == "all":
        if user.role.name not in ("admin", "researcher"):
            raise HTTPException(403, "scope=all requires researcher or admin role")
        return None
    return user.id


def load_evaluation() -> dict:
    out = {}
    for name in ("detector_evaluation", "species_evaluation", "detector_inference_tradeoff", "yolo11_evaluation"):
        p = REPORTS_DIR / f"{name}.json"
        if p.exists():
            out[name] = json.loads(p.read_text())
    return out


def dashboard_metrics(db: Session, owner: int | None) -> dict:
    def own(stmt, col):
        return stmt.where(col == owner) if owner is not None else stmt

    scans_q = own(select(func.count(Scan.id)), Scan.owner_id)
    flowers_q = own(select(func.coalesce(func.sum(Scan.flower_count), 0)), Scan.owner_id)
    det_join = select(FlowerDetection.species_id, func.count()).join(Scan, Scan.id == FlowerDetection.scan_id)
    species = dict(db.execute(own(det_join, Scan.owner_id).group_by(FlowerDetection.species_id)).all())
    stage = dict(db.execute(own(select(MaturityPrediction.stage, func.count())
                                .join(FlowerDetection, FlowerDetection.id == MaturityPrediction.detection_id)
                                .join(Scan, Scan.id == FlowerDetection.scan_id), Scan.owner_id)
                            .group_by(MaturityPrediction.stage)).all())
    ready = dict(db.execute(own(select(ReadinessPrediction.category, func.count())
                                .join(FlowerDetection, FlowerDetection.id == ReadinessPrediction.detection_id)
                                .join(Scan, Scan.id == FlowerDetection.scan_id), Scan.owner_id)
                            .group_by(ReadinessPrediction.category)).all())
    sims = db.scalars(own(select(Simulation), Simulation.owner_id)).all()
    sim_by_species: dict[str, list] = defaultdict(list)
    for s in sims:
        if s.status == "completed":
            sim_by_species[s.species_id].append(s.result_summary.get("simulated_transfer_efficiency", 0))
    since = datetime.now(timezone.utc) - timedelta(days=30)
    recent = db.scalars(own(select(Scan), Scan.owner_id).where(Scan.created_at >= since)).unique().all()
    per_day = Counter(s.created_at.strftime("%Y-%m-%d") for s in recent)
    methods = Counter(s.detection_method for s in recent)
    latest = db.scalars(own(select(Scan), Scan.owner_id).order_by(Scan.created_at.desc()).limit(8)).unique().all()
    return {
        "totals": {
            "scanned_images": db.scalar(scans_q) or 0, "detected_flowers": int(db.scalar(flowers_q) or 0),
            "analysed_flowers": sum(species.values()), "simulation_runs": len(sims),
            "completed_simulations": sum(s.status == "completed" for s in sims),
            "pollination_records": db.scalar(own(select(func.count(PollinationRecord.id)), PollinationRecord.owner_id)) or 0,
            "environment_records": db.scalar(own(select(func.count(EnvironmentRecord.id)), EnvironmentRecord.owner_id)) or 0,
        },
        "species_distribution": species, "stage_distribution": stage, "readiness_distribution": ready,
        "simulations_by_species": {k: {"runs": len(v), "mean_simulated_transfer_efficiency": round(sum(v) / len(v), 4)}
                                   for k, v in sim_by_species.items()},
        "scans_per_day_30d": dict(sorted(per_day.items())), "detection_methods_30d": dict(methods),
        "recent_scans": [scan_dict(s) for s in latest],
        "provenance": "database records for this account" if owner is not None else "database records, all accounts",
    }


@router.get("/analytics/dashboard")
def dashboard(scope: str = Query("mine", pattern="^(mine|all)$"), user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    m = dashboard_metrics(db, _scope(user, scope))
    evs = load_evaluation()
    trade, ev = evs.get("detector_inference_tradeoff"), evs.get("detector_evaluation")
    if trade:  # deployed inference configuration (chosen on validation)
        ch = trade["chosen"]["full"]
        row = next(c for c in trade["configs"] if c["side"] == ch["side"] and c["stride"] == ch["stride"])
        m["model_performance"] = {"source": f"ai-engine/reports/detector_inference_tradeoff.json - deployed config "
                                            f"{ch['side']}px/stride {ch['stride']}, held-out test split",
                                  "mAP50": row["test"]["mAP50"], "mAP50_95": row["test"]["mAP50_95"],
                                  "generated_at": trade["generated_at"]}
    elif ev:
        dep = ev["variants"][ev["deployed_variant"]]["test"]
        m["model_performance"] = {"source": "ai-engine/reports/detector_evaluation.json (held-out test split)",
                                  "mAP50": dep["mAP50"], "mAP50_95": dep["mAP50_95"],
                                  "generated_at": ev["generated_at"]}
    return m


@router.get("/analytics/species")
def species_analytics(scope: str = Query("mine", pattern="^(mine|all)$"), user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    owner = _scope(user, scope)
    stmt = (select(FlowerDetection.species_id, MaturityPrediction.stage, ReadinessPrediction.category,
                   FlowerDetection.species_confidence)
            .join(Scan, Scan.id == FlowerDetection.scan_id)
            .outerjoin(MaturityPrediction, MaturityPrediction.detection_id == FlowerDetection.id)
            .outerjoin(ReadinessPrediction, ReadinessPrediction.detection_id == FlowerDetection.id))
    if owner is not None:
        stmt = stmt.where(Scan.owner_id == owner)
    agg: dict = defaultdict(lambda: {"count": 0, "stages": Counter(), "readiness": Counter(), "conf_sum": 0.0})
    for sp, stage, cat, conf in db.execute(stmt).all():
        a = agg[sp]
        a["count"] += 1
        a["conf_sum"] += conf or 0
        if stage:
            a["stages"][stage] += 1
        if cat:
            a["readiness"][cat] += 1
    return {sp: {"count": a["count"], "mean_species_confidence": round(a["conf_sum"] / a["count"], 4),
                 "stages": dict(a["stages"]), "readiness": dict(a["readiness"])} for sp, a in agg.items()}


@router.get("/analytics/model-performance", summary="Saved evaluation results (never placeholder values)")
def model_performance(user: User = Depends(get_current_user)):
    ev = load_evaluation()
    if not ev:
        return {"available": False, "detail": "No evaluation reports found. Run ai-engine/training/*.py."}
    return {"available": True, **ev}


@router.get("/reports/scans.csv", response_class=Response)
def report_csv(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    scans = db.scalars(select(Scan).where(Scan.owner_id == user.id).order_by(Scan.created_at.desc())).unique().all()
    log(db, user, "report.csv")
    db.commit()
    return Response(scans_csv(scans), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="pollinex_scans.csv"'})


@router.get("/reports/summary.pdf", response_class=Response)
def report_pdf(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    metrics = dashboard_metrics(db, user.id)
    scans = db.scalars(select(Scan).where(Scan.owner_id == user.id).order_by(Scan.created_at.desc()).limit(40)).unique().all()
    sims = db.scalars(select(Simulation).where(Simulation.owner_id == user.id).order_by(Simulation.created_at.desc()).limit(30)).all()
    ev = load_evaluation().get("detector_evaluation")
    evs = None
    if ev:
        t = ev["variants"][ev["deployed_variant"]]["test"]
        evs = {k: t[k] for k in ("mAP50", "mAP50_95", "precision@0.5", "recall@0.5", "f1@0.5")}
    pdf = summary_pdf(user.email, metrics, scans, sims, evs)
    log(db, user, "report.pdf")
    db.commit()
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="pollinex_report.pdf"'})


@router.get("/reports/scans/{scan_id}.json")
def report_scan_json(scan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.get(Scan, scan_id)
    if not s or s.owner_id != user.id:
        raise HTTPException(404, "scan not found")
    return Response(json.dumps(scan_dict(s, with_flowers=True), default=str, indent=2), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="pollinex_scan_{scan_id}.json"'})
