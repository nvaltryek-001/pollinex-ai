"""Idempotent reference-data seeding: roles, species KB, dataset manifest, research references, evaluation runs.

Seeds *reference* data only. It never inserts scans, detections or metrics that did not happen.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import REPO_ROOT, get_settings
from ..models import DatasetMetadata, EvaluationRun, ResearchReference, Role, Species, User
from ..security import hash_password
from . import engine

log = logging.getLogger("pollinex.seed")


def seed(db: Session) -> None:
    for name, desc in (("admin", "Full administration"), ("researcher", "Datasets, models, galleries, all-account analytics"),
                       ("user", "Own scans, fields, simulations and reports")):
        if not db.scalar(select(Role).where(Role.name == name)):
            db.add(Role(name=name, description=desc))
    db.flush()

    for s in engine.load_kb()["species"]:
        row = db.get(Species, s["id"])
        if row is None:
            db.add(Species(id=s["id"], common_name=s["common_name"], scientific_name=s["scientific_name"],
                           primary_mechanism=s["primary_mechanism"], knowledge=s))
        else:
            row.knowledge, row.primary_mechanism = s, s["primary_mechanism"]

    src = REPO_ROOT / "datasets" / "dataset_sources.json"
    if src.exists():
        for d in json.loads(src.read_text())["datasets"]:
            row = db.get(DatasetMetadata, d["id"])
            payload = dict(name=d["name"], url=d["url"], license=d["license"], task_support=d["task_support"],
                           status=d["status"], details=d)
            if row is None:
                db.add(DatasetMetadata(id=d["id"], **payload))
            else:
                for k, v in payload.items():
                    setattr(row, k, v)

    refs = REPO_ROOT / "research" / "references.json"
    if refs.exists():
        for r in json.loads(refs.read_text()):
            if not db.get(ResearchReference, r["id"]):
                db.add(ResearchReference(**r))

    reports = REPO_ROOT / "ai-engine" / "reports"
    for task, fname in (("detection", "detector_evaluation.json"), ("species", "species_evaluation.json")):
        p = reports / fname
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        if db.scalar(select(EvaluationRun).where(EvaluationRun.task == task, EvaluationRun.report_path == str(p.relative_to(REPO_ROOT)))):
            continue
        if task == "detection":
            t = data["variants"][data["deployed_variant"]]["test"]
            metrics = {k: t[k] for k in ("mAP50", "mAP50_95", "precision@0.5", "recall@0.5", "f1@0.5")}
        else:
            metrics = {"open_set_accuracy": data["test_open_set"]["accuracy"], "open_set_macro_f1": data["test_open_set"]["macro_f1"],
                       "background_rejection": data["test_background_rejection_rate"]}
        db.add(EvaluationRun(task=task, dataset_id="usda_fruit_flower", split="test", metrics=metrics,
                             report_path=str(p.relative_to(REPO_ROOT))))

    s = get_settings()
    if s.admin_email and s.admin_password and not db.scalar(select(User).where(User.email == s.admin_email.lower())):
        role = db.scalar(select(Role).where(Role.name == "admin"))
        db.add(User(email=s.admin_email.lower(), full_name="Administrator", password_hash=hash_password(s.admin_password),
                    role_id=role.id))
        log.info("bootstrap admin created from environment")
    db.commit()
