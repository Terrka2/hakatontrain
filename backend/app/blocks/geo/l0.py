"""L0: чистая математика гео-утилит без внешних зависимостей, сети и базы данных."""

import math

from app.contracts.models import GeoPoint

EARTH_RADIUS_M = 6371000.0


def haversine_m(a: GeoPoint, b: GeoPoint) -> float:
    """Вычисляет расстояние между двумя точками на сфере по формуле гаверсинусов (в метрах)."""
    phi1 = math.radians(a.lat)
    phi2 = math.radians(b.lat)
    delta_phi = math.radians(b.lat - a.lat)
    delta_lambda = math.radians(b.lon - a.lon)

    hav = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    hav = min(1.0, max(0.0, hav))
    c = 2.0 * math.atan2(math.sqrt(hav), math.sqrt(1.0 - hav))
    return EARTH_RADIUS_M * c


def centroid(points: list[GeoPoint]) -> GeoPoint:
    """Вычисляет геометрический центр (центроид) для списка точек."""
    if not points:
        raise ValueError("points cannot be empty")
    avg_lat = sum(p.lat for p in points) / len(points)
    avg_lon = sum(p.lon for p in points) / len(points)
    return GeoPoint(lat=avg_lat, lon=avg_lon)


def within(center: GeoPoint, points: list[GeoPoint], radius_m: float) -> list[int]:
    """Возвращает индексы точек из points, расстояние от center до которых <= radius_m."""
    return [idx for idx, pt in enumerate(points) if haversine_m(center, pt) <= radius_m]


def distance_to_polyline_m(p: GeoPoint, line: list[GeoPoint]) -> tuple[float, float]:
    """Вычисляет (кратчайшее расстояние до полилинии, расстояние от начала вдоль линии) в метрах."""
    if not line:
        raise ValueError("Empty line")
    if len(line) == 1:
        return (haversine_m(p, line[0]), 0.0)

    min_dist = float("inf")
    best_along = 0.0
    accum_dist = 0.0

    for i in range(len(line) - 1):
        a = line[i]
        b = line[i + 1]
        seg_len = haversine_m(a, b)

        mid_lat = math.radians((a.lat + b.lat) / 2.0)
        cos_mid = math.cos(mid_lat)

        xb = math.radians(b.lon - a.lon) * EARTH_RADIUS_M * cos_mid
        yb = math.radians(b.lat - a.lat) * EARTH_RADIUS_M

        xp = math.radians(p.lon - a.lon) * EARTH_RADIUS_M * cos_mid
        yp = math.radians(p.lat - a.lat) * EARTH_RADIUS_M

        l2 = xb * xb + yb * yb
        if l2 == 0.0:
            t = 0.0
            dist = math.hypot(xp, yp)
        else:
            t = max(0.0, min(1.0, (xp * xb + yp * yb) / l2))
            proj_x = t * xb
            proj_y = t * yb
            dist = math.hypot(xp - proj_x, yp - proj_y)

        if dist < min_dist:
            min_dist = dist
            best_along = accum_dist + t * seg_len

        accum_dist += seg_len

    return (min_dist, best_along)


def geocode(address: str) -> GeoPoint | None:
    """В L0 геокодер отключён и всегда возвращает None."""
    _ = address
    return None


def h3_cell(p: GeoPoint, res: int = 9) -> str:
    """В L0 аппроксимация h3 ячейки округлением координат."""
    return f"{round(p.lat, 4):.4f}_{round(p.lon, 4):.4f}_{res}"
