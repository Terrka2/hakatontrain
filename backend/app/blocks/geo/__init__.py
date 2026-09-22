"""Блок B2 · Гео-утилиты. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B2_geo.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from app.contracts.models import GeoPoint


def haversine_m(a: GeoPoint, b: GeoPoint) -> float:
    raise NotImplementedError("B2: реализуй по контракту docs/contracts/B2_geo.md")


def centroid(points: list[GeoPoint]) -> GeoPoint:
    raise NotImplementedError("B2: реализуй по контракту docs/contracts/B2_geo.md")


def within(center: GeoPoint, points: list[GeoPoint], radius_m: float) -> list[int]:
    raise NotImplementedError("B2: реализуй по контракту docs/contracts/B2_geo.md")


def distance_to_polyline_m(p: GeoPoint, line: list[GeoPoint]) -> tuple[float, float]:
    raise NotImplementedError("B2: реализуй по контракту docs/contracts/B2_geo.md")


def geocode(address: str) -> GeoPoint | None:
    raise NotImplementedError("B2: реализуй по контракту docs/contracts/B2_geo.md")


def h3_cell(p: GeoPoint, res: int = 9) -> str:
    raise NotImplementedError("B2: реализуй по контракту docs/contracts/B2_geo.md")
