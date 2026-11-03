"""Bridge to the ai-engine and simulation packages (kept as separate, independently testable packages)."""
from __future__ import annotations

import sys
import threading
from functools import lru_cache

from ..config import REPO_ROOT

for sub in ("ai-engine", "simulation"):
    p = str(REPO_ROOT / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from pollinex_ai.knowledge import get_species, load_kb  # noqa: E402
from pollinex_ai.pipeline import GALLERY_PATH, Analyzer  # noqa: E402
from pollinex_ai.readiness import estimate_readiness  # noqa: E402
from pollinex_ai.species import SpeciesGallery  # noqa: E402
from pollinex_sim import SimParams, parameter_sweep, run_simulation  # noqa: E402

_lock = threading.Lock()


@lru_cache(maxsize=1)
def get_analyzer() -> Analyzer:
    """Loads the detector + species gallery once. Uses the user-extended gallery when it exists."""
    from ..config import get_settings

    user_gallery = get_settings().gallery_dir / "species_gallery"
    path = user_gallery if user_gallery.with_suffix(".json").exists() else GALLERY_PATH
    return Analyzer(gallery_path=path)


def analyze(rgb, **kw) -> dict:
    an = get_analyzer()
    with _lock:  # HistGradientBoosting + OpenCV already use threads; serialise to bound memory on laptops
        return an.analyze(rgb, **kw)


def add_reference(species_id: str, crop, source: str) -> dict:
    from ..config import get_settings

    an = get_analyzer()
    with _lock:
        an.gallery.add(species_id, crop, source)
        an.gallery.save(get_settings().gallery_dir / "species_gallery")
        return an.gallery.counts()


__all__ = ["SimParams", "SpeciesGallery", "analyze", "add_reference", "estimate_readiness", "get_analyzer",
           "get_species", "load_kb", "parameter_sweep", "run_simulation"]
