"""Optional Open-Meteo integration (free, no API key). Never fabricates readings: on failure it raises."""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status

from ..config import get_settings


def fetch_current(lat: float, lon: float) -> dict:
    s = get_settings()
    if not s.weather_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Weather API integration is disabled (WEATHER_API_ENABLED=false)")
    params = {"latitude": lat, "longitude": lon,
              "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
              "wind_speed_unit": "kmh", "timezone": "UTC"}
    try:
        r = httpx.get(s.weather_base_url, params=params, timeout=10)
        r.raise_for_status()
        cur = r.json()["current"]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Weather provider unavailable: {type(e).__name__}")
    observed = datetime.fromisoformat(cur["time"]).replace(tzinfo=timezone.utc)
    return {"observed_at": observed, "temperature_c": cur.get("temperature_2m"),
            "relative_humidity_pct": cur.get("relative_humidity_2m"), "rain_mm_h": cur.get("precipitation"),
            "wind_kmh": cur.get("wind_speed_10m"),
            "source_detail": {"provider": "Open-Meteo", "endpoint": s.weather_base_url, "latitude": lat, "longitude": lon,
                              "retrieved_at": datetime.now(timezone.utc).isoformat(),
                              "licence": "CC BY 4.0 (Open-Meteo data)", "model_time": cur["time"]}}
