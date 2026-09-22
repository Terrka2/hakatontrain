"""L1: целевой уровень гео-утилит (geopy Nominatim, h3).

Любая ошибка L1 перехватывается в __init__.py с тихим откатом на l0.py.
"""

import logging

import h3  # type: ignore[import-untyped]
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]

from app.contracts.models import GeoPoint

from . import l0

log = logging.getLogger(__name__)

# Bounding box Кишинёва: lat 46.9-47.1, lon 28.7-28.9
CHISINAU_MIN_LAT = 46.9
CHISINAU_MAX_LAT = 47.1
CHISINAU_MIN_LON = 28.7
CHISINAU_MAX_LON = 28.9

# In-memory кэш геокодированных адресов
_cache: dict[str, GeoPoint | None] = {}


def clear_cache() -> None:
    """Очищает кэш геокодирования."""
    _cache.clear()


def is_in_chisinau(lat: float, lon: float) -> bool:
    """Проверяет попадание координат в bounding box Кишинёва."""
    return (
        CHISINAU_MIN_LAT <= lat <= CHISINAU_MAX_LAT
        and CHISINAU_MIN_LON <= lon <= CHISINAU_MAX_LON
    )


def haversine_m(a: GeoPoint, b: GeoPoint) -> float:
    """Делегирует расчёт расстояния в L0."""
    return l0.haversine_m(a, b)


def centroid(points: list[GeoPoint]) -> GeoPoint:
    """Делегирует расчёт центроида в L0."""
    return l0.centroid(points)


def within(center: GeoPoint, points: list[GeoPoint], radius_m: float) -> list[int]:
    """Делегирует поиск точек в радиусе в L0."""
    return l0.within(center, points, radius_m)


def distance_to_polyline_m(p: GeoPoint, line: list[GeoPoint]) -> tuple[float, float]:
    """Делегирует расчёт расстояния до полилинии в L0."""
    return l0.distance_to_polyline_m(p, line)


def geocode(address: str) -> GeoPoint | None:
    """Геокодирование адреса через Nominatim с кэшем и ограничением Кишинёва.

    Исключения пробрасываются в __init__.py для логирования со стеком и отката на L0.
    """
    if not address or not address.strip():
        return None

    clean_address = address.strip()
    if clean_address in _cache:
        return _cache[clean_address]

    geolocator = Nominatim(user_agent="citytriage_geo_l1", timeout=5)
    location = geolocator.geocode(clean_address, country_codes="md")
    if location is None:
        _cache[clean_address] = None
        return None

    lat = float(location.latitude)
    lon = float(location.longitude)
    if not is_in_chisinau(lat, lon):
        _cache[clean_address] = None
        return None

    point = GeoPoint(lat=lat, lon=lon)
    _cache[clean_address] = point
    return point


def h3_cell(p: GeoPoint, res: int = 9) -> str:
    """Определение ячейки H3 через библиотеку h3."""
    cell = h3.latlng_to_cell(p.lat, p.lon, res)
    return str(cell)
