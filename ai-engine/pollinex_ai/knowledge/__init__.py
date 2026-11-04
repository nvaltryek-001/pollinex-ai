"""Species knowledge base loader."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

KB_PATH = Path(__file__).with_name("species_kb.json")
BOTANY_PATH = Path(__file__).with_name("species_botany.json")
BOTANY_FIELDS = ("family", "flower", "petals", "reproductive_structures", "flowering", "flowering_period",
                 "pollination_mechanism", "pollinators", "breeding_system", "fruit", "agricultural_relevance", "sources")


def load_botany(path: str | None = None) -> dict:
    """General botanical reference data (separate from image-derived results; see 'scope' in the JSON)."""
    data = json.loads(Path(path or BOTANY_PATH).read_text(encoding="utf-8"))
    for sid, rec in data["species"].items():
        missing = [f for f in BOTANY_FIELDS if f not in rec]
        if missing:
            raise ValueError(f"botany record {sid} misses {missing}")
        for src in rec["sources"]:
            if src not in data["sources"]:
                raise ValueError(f"botany record {sid}: unknown source {src}")
    return data


@lru_cache(maxsize=1)
def load_kb(path: str | None = None) -> dict:
    kb = json.loads(Path(path or KB_PATH).read_text(encoding="utf-8"))
    ids = [s["id"] for s in kb["species"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate species ids in knowledge base")
    for s in kb["species"]:
        for ev in s.get("evidence", []):
            if ev not in kb["evidence_sources"]:
                raise ValueError(f"{s['id']}: unknown evidence key {ev}")
    if path is None and BOTANY_PATH.exists():
        bot = load_botany()
        kb["botany_scope"], kb["fruit_recognition"], kb["botany_sources"] = bot["scope"], bot["fruit_recognition"], bot["sources"]
        for s in kb["species"]:
            if s["id"] in bot["species"]:
                rec = dict(bot["species"][s["id"]])
                rec["sources"] = [{"id": k, **bot["sources"][k]} for k in rec["sources"]]
                s["botany"] = rec
    return kb


def get_species(species_id: str) -> dict | None:
    sid = (species_id or "").lower()
    for s in load_kb()["species"]:
        if s["id"] == sid or sid in [a.lower() for a in s.get("aliases", [])]:
            return s
    return None


def species_ids() -> list[str]:
    return [s["id"] for s in load_kb()["species"]]
