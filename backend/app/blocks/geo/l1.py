"""L1: целевой уровень гео-утилит (geopy Nominatim, h3).

Любая ошибка L1 перехватывается в __init__.py с тихим откатом на l0.py.
"""

from app.contracts.models import GeoPoint

from . import l0


def haversine_m(a: GeoPoint, b: GeoPoint) -> float:
    return l0.haversine_m(a, b)


def centroid(points: list[GeoPoint]) -> GeoPoint:
    return l0.centroid(points)


def within(center: GeoPoint, points: list[GeoPoint], radius_m: float) -> list[int]:
    return l0.within(center, points, radius_m)


def distance_to_polyline_m(p: GeoPoint, line: list[GeoPoint]) -> tuple[float, float]:
    return l0.distance_to_polyline_m(p, line)


def geocode(address: str) -> GeoPoint | None:
    return l0.geocode(address)


def h3_cell(p: GeoPoint, res: int = 9) -> str:
    return l0.h3_cell(p, res)
