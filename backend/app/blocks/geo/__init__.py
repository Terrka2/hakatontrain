"""Блок B2 · Гео-утилиты. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B2_geo.md. Реализация: l0.py (чистая математика), l1.py (geopy, h3).
"""

import logging

from app.contracts.models import GeoPoint
from app.core.config import settings

from . import l0, l1

log = logging.getLogger(__name__)


def haversine_m(a: GeoPoint, b: GeoPoint) -> float:
    """Вычисляет расстояние между двумя точками по формуле гаверсинусов (в метрах)."""
    return l0.haversine_m(a, b)


def centroid(points: list[GeoPoint]) -> GeoPoint:
    """Вычисляет геометрический центр (центроид) для списка точек."""
    return l0.centroid(points)


def within(center: GeoPoint, points: list[GeoPoint], radius_m: float) -> list[int]:
    """Возвращает индексы точек, находящихся в радиусе radius_m от center."""
    return l0.within(center, points, radius_m)


def distance_to_polyline_m(p: GeoPoint, line: list[GeoPoint]) -> tuple[float, float]:
    """Вычисляет (расстояние до полилинии, расстояние от начала вдоль линии) в метрах."""
    return l0.distance_to_polyline_m(p, line)


def geocode(address: str) -> GeoPoint | None:
    """Геокодирование адреса. При GEOCODER=off, USE_MOCK=true или ошибке L1 — откат на L0 (None)."""
    if settings.USE_MOCK or settings.GEOCODER == "off":
        return l0.geocode(address)
    try:
        return l1.geocode(address)
    except Exception:  # noqa: BLE001
        log.warning("B2: L1 geocode failed, falling back to L0", exc_info=True)
        return l0.geocode(address)


def h3_cell(p: GeoPoint, res: int = 9) -> str:
    """Определение ячейки H3. При USE_MOCK=true или ошибке L1 — откат на L0."""
    if settings.USE_MOCK:
        return l0.h3_cell(p, res)
    try:
        return l1.h3_cell(p, res)
    except Exception:  # noqa: BLE001
        log.warning("B2: L1 h3_cell failed, falling back to L0", exc_info=True)
        return l0.h3_cell(p, res)
