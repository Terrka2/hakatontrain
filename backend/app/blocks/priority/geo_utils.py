"""Гео-утилиты для расчёта расстояний в факторах приоритета."""

import math

from app.contracts.models import GeoPoint


def haversine_m(a: GeoPoint, b: GeoPoint) -> float:
    """Вычисляет расстояние между двумя координатами в метрах."""
    try:
        from app.blocks.geo import haversine_m as geo_haversine

        return geo_haversine(a, b)
    except NotImplementedError, ImportError, Exception:
        r = 6371000.0
        p1, p2 = math.radians(a.lat), math.radians(b.lat)
        dp = math.radians(b.lat - a.lat)
        dl = math.radians(b.lon - a.lon)
        s = (
            math.sin(dp / 2.0) ** 2
            + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
        )
        return 2.0 * r * math.atan2(math.sqrt(s), math.sqrt(1.0 - s))
