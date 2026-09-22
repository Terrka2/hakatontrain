"""L1: прогноз погоды через Open-Meteo с in-memory кэшем на 30 минут."""

import logging
import time
from datetime import datetime

import httpx

from app.contracts.models import GeoPoint, Weather

log = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 30 * 60  # 30 минут
_cache: dict[tuple[float, float], tuple[float, Weather]] = {}


def clear_cache() -> None:
    """Очистить кэш прогнозов погоды (для изоляции тестов)."""
    _cache.clear()


def get_weather(point: GeoPoint, at: datetime) -> Weather | None:
    """Получить прогноз погоды из кэша или запросить Open-Meteo API."""
    key = (point.lat, point.lon)
    now_mono = time.monotonic()

    if key in _cache:
        cached_time, cached_weather = _cache[key]
        if now_mono - cached_time < CACHE_TTL_SECONDS:
            return cached_weather.model_copy(update={"at": at})

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={point.lat}&longitude={point.lon}"
        f"&current=temperature_2m,precipitation,wind_speed_10m"
    )

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            curr = resp.json().get("current", {})
            weather = Weather(
                at=at,
                precipitation_mm=float(curr.get("precipitation", 0.0)),
                wind_ms=float(curr.get("wind_speed_10m", 0.0)),
                temp_c=float(curr.get("temperature_2m", 0.0)),
                source="open-meteo",
            )
            _cache[key] = (now_mono, weather)
            return weather
    except Exception as exc:  # noqa: BLE001
        log.warning("Open-Meteo request failed for %s: %s", point, exc)
        return None
