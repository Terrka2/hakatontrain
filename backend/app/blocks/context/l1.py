"""L1: целевой уровень B5 (Open-Meteo)."""

from datetime import datetime

import httpx

from app.contracts.models import GeoPoint, Weather


def get_weather(point: GeoPoint, at: datetime) -> Weather:
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={point.lat}&longitude={point.lon}"
        f"&current=temperature_2m,wind_speed_10m,precipitation"
    )
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        curr = resp.json().get("current", {})
    return Weather(
        at=at,
        precipitation_mm=float(curr.get("precipitation", 0.0)),
        wind_ms=float(curr.get("wind_speed_10m", 0.0)),
        temp_c=float(curr.get("temperature_2m", 0.0)),
        source="open-meteo",
    )
