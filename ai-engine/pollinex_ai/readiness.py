"""Species-specific *visual* pollination-readiness estimate and explainable recommendation.

This is a transparent rule engine over: species knowledge base, estimated stage, centre-region
cues, visible health indicators and (optional) environmental conditions. There are no biological
ground-truth labels, so the output is always called a **visual readiness estimate**.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .knowledge import get_species, load_kb

STALE_HOURS = 6
CATEGORIES = ["likely_ready", "approaching", "past_window", "not_ready", "indeterminate"]


def _env_assessment(env: dict | None, species: dict | None) -> tuple[list[dict], float]:
    if not env:
        return [{"factor": "environment", "effect": "unknown", "detail": "No environmental record attached."}], 1.0
    rules = {k: dict(v) for k, v in load_kb()["default_environment_rules"].items()}
    if species:
        for k, v in species.get("environment_overrides", {}).items():
            rules[k] = {**rules.get(k, {}), **v}
    factors, mult = [], 1.0
    checks = [("temperature_c", "temperature"), ("relative_humidity_pct", "humidity"),
              ("rain_mm_h", "rain"), ("wind_kmh", "wind")]
    for key, name in checks:
        val = env.get(key)
        if val is None:
            continue
        r = rules.get(key, {})
        if "low" in r and val < r["low"]:
            factors.append({"factor": name, "effect": "unfavourable", "value": val,
                            "detail": f"{val} below {r['low']} ({r.get('note', '')})", "evidence": r.get("evidence")})
            mult *= 0.8
        elif "high" in r and val > r["high"]:
            factors.append({"factor": name, "effect": "unfavourable", "value": val,
                            "detail": f"{val} above {r['high']} ({r.get('note', '')})", "evidence": r.get("evidence")})
            mult *= 0.8
        else:
            factors.append({"factor": name, "effect": "within_general_range", "value": val})
    missing = [name for key, name in checks if env.get(key) is None]
    if missing:
        factors.append({"factor": "missing_data", "effect": "unknown",
                        "detail": "No reading for: " + ", ".join(missing) + " - these factors were not assessed."})
    obs = env.get("observed_at")
    if obs:
        try:
            ts = datetime.fromisoformat(str(obs).replace("Z", "+00:00"))
            if ts.tzinfo is None:  # SQLite returns naive datetimes; values are stored in UTC
                ts = ts.replace(tzinfo=timezone.utc)
            age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            if age_h > STALE_HOURS:
                factors.append({"factor": "stale_data", "effect": "unknown",
                                "detail": f"Record is {age_h:.0f} h old; current conditions may differ."})
        except ValueError:
            pass
    src = env.get("source", "unspecified")
    factors.append({"factor": "environment_source", "effect": "info", "detail": f"source={src}, observed_at={obs}"})
    return factors, mult


def estimate_readiness(species_id: str | None, stage: dict, centre: dict | None = None, health: dict | None = None,
                       env: dict | None = None, detection_score: float = 1.0, species_confidence: float = 1.0) -> dict[str, Any]:
    sp = get_species(species_id) if species_id and species_id != "unknown" else None
    observations, warnings = [], []
    stg = stage.get("stage")
    observations.append(f"Estimated stage '{stg}' (heuristic score {stage.get('score')})")
    if stage.get("uncertain"):
        warnings.append("Stage estimate is uncertain (top-two stage scores are close).")
    if centre:
        if centre.get("yellow_cluster_visible"):
            observations.append("Yellow cluster visible in the flower centre (possible pollen-bearing anthers).")
        elif centre.get("centre_region"):
            observations.append("Distinct centre region visible; no yellow pollen-like cluster detected.")
    if health and health.get("indicators"):
        observations.append("Visible anomalies: " + ", ".join(i["type"] for i in health["indicators"]))

    if sp is None:
        category = "indeterminate"
        warnings.append("Species unknown - species-specific rules cannot be applied; no strategy is recommended.")
        strategy = None
    else:
        if stg in sp["ready_stages"]:
            category = "likely_ready"
        elif stg in sp["approaching_stages"]:
            category = "approaching"
        elif stg in sp["past_stages"]:
            category = "past_window"
        else:
            category = "not_ready"
        strategy = {"mechanism": sp["primary_mechanism"], "pollination_types": sp["pollination_types"],
                    "compatibility": sp["compatibility"], "recommendation": sp["strategy"],
                    "detail": sp["mechanism_detail"]}
        if health and any(i["type"] == "browning" for i in health.get("indicators", [])) and category == "likely_ready":
            category = "past_window"
            warnings.append("Browning suggests the flower may be past its window despite the open-stage estimate.")

    env_factors, env_mult = _env_assessment(env, sp)
    if any(f["factor"] in ("missing_data", "stale_data") for f in env_factors):
        warnings.append("Environmental data is incomplete or out of date; environmental factors are only partly assessed.")
    if any(f["effect"] == "unfavourable" for f in env_factors):
        warnings.append("Environmental conditions outside general favourable ranges - consider waiting.")
    conf = float(stage.get("score", 0.5)) * float(detection_score) * float(species_confidence) * env_mult
    if conf < 0.35:
        warnings.append("Low overall confidence - treat this estimate as a prompt for manual inspection.")
    kb = load_kb()
    return {
        "category": category, "confidence": round(conf, 4),
        "label": "visual readiness estimate (not a validated biological prediction)",
        "species": sp["id"] if sp else "unknown", "stage": stg,
        "supporting_observations": observations, "factors": env_factors, "uncertainty_warnings": warnings,
        "strategy": strategy,
        "biological_limitations": (sp or {}).get("limitations", []) + [
            "Image appearance does not prove pollen viability, stigma receptivity or successful fertilisation."],
        "research_sources": [kb["evidence_sources"][e] for e in (sp or {}).get("evidence", [])],
        "evidence_level": (sp or {}).get("evidence_level"), "method": "rule_engine",
    }
