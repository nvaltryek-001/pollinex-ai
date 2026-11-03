"""Species knowledge base loader."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

KB_PATH = Path(__file__).with_name("species_kb.json")


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
    return kb


def get_species(species_id: str) -> dict | None:
    sid = (species_id or "").lower()
    for s in load_kb()["species"]:
        if s["id"] == sid or sid in [a.lower() for a in s.get("aliases", [])]:
            return s
    return None


def species_ids() -> list[str]:
    return [s["id"] for s in load_kb()["species"]]
