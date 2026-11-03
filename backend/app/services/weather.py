"""Optional Open-Meteo integration (free, no API key). Never fabricates readings: on failure it raises."""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status

from ..config import get_settings


# WMO weather interpretation codes as documented by Open-Meteo
WMO_CODES = {0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "depositing rime fog",
             51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle", 56: "light freezing drizzle",
             57: "dense freezing drizzle", 61: "slight rain", 63: "moderate rain", 65: "heavy rain",
             66: "light freezing rain", 67: "heavy freezing rain", 71: "slight snow", 73: "moderate snow",
             75: "heavy snow", 77: "snow grains", 80: "slight rain showers", 81: "moderate rain showers",
             82: "violent rain showers", 85: "slight snow showers", 86: "heavy snow showers", 95: "thunderstorm",
             96: "thunderstorm with slight hail", 99: "thunderstorm with heavy hail"}


def fetch_current(lat: float, lon: float) -> dict:
    s = get_settings()
    if not s.weather_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Weather API integration is disabled (WEATHER_API_ENABLED=false)")
    params = {"latitude": lat, "longitude": lon,
              "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
              "wind_speed_unit": "kmh", "timezone": "UTC"}
    try:
        r = httpx.get(s.weather_base_url, params=params, timeout=10)
        r.raise_for_status()
        cur = r.json()["current"]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Weather provider unavailable: {type(e).__name__}")
    observed = datetime.fromisoformat(cur["time"]).replace(tzinfo=timezone.utc)
    code = cur.get("weather_code")
    condition = WMO_CODES.get(code, f"WMO code {code}") if code is not None else None
    return {"observed_at": observed, "temperature_c": cur.get("temperature_2m"),
            "relative_humidity_pct": cur.get("relative_humidity_2m"), "rain_mm_h": cur.get("precipitation"),
            "wind_kmh": cur.get("wind_speed_10m"), "observation": f"Conditions: {condition}" if condition else "",
            "source_detail": {"provider": "Open-Meteo", "endpoint": s.weather_base_url, "latitude": lat, "longitude": lon,
                              "retrieved_at": datetime.now(timezone.utc).isoformat(),
                              "licence": "CC BY 4.0 (Open-Meteo data)", "model_time": cur["time"],
                              "weather_code": code, "condition": condition,
                              "missing_fields": [k for k in ("temperature_2m", "relative_humidity_2m", "precipitation",
                                                             "wind_speed_10m") if cur.get(k) is None]}}
