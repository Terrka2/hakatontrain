"""Тесты блока B2 (geo).

Один критерий приёмки = минимум один тест.
Все тесты проходят БЕЗ сети и БЕЗ базы данных.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.blocks import geo
from app.contracts.models import GeoPoint
from app.core.config import settings

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "app" / "fixtures" / "demo_city.json"
)


@pytest.fixture(autouse=True)
def disable_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Запрещает любые сетевые вызовы в тестах блока."""

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("Network access forbidden in block tests")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)


@pytest.fixture
def fixture_data() -> dict[str, Any]:
    """Загрузка demo_city.json."""
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# ==============================================================================
# 1. Критерии приёмки
# ==============================================================================


def test_criterion_1_haversine_fixture_distances(fixture_data: dict[str, Any]) -> None:
    """Критерий 1: haversine_m между r001 и r002 = 27–31 м; между r007 и r010 = 385–393 м."""
    reports = {r["id"]: GeoPoint(**r["location"]) for r in fixture_data["reports"]}

    dist_1_2 = geo.haversine_m(reports["r001"], reports["r002"])
    assert 27.0 <= dist_1_2 <= 31.0, f"Expected 27-31m, got {dist_1_2}m"

    dist_7_10 = geo.haversine_m(reports["r007"], reports["r010"])
    assert 385.0 <= dist_7_10 <= 393.0, f"Expected 385-393m, got {dist_7_10}m"


def test_criterion_2_within_event_radius(fixture_data: dict[str, Any]) -> None:
    """Критерий 2: within вокруг события e1 с радиусом 400 м находит r012 и r013 и не находит r001."""
    e1_data = next(e for e in fixture_data["events"] if e["id"] == "e1")
    center = GeoPoint(**e1_data["location"])

    reports = fixture_data["reports"]
    report_points = [GeoPoint(**r["location"]) for r in reports]
    id_to_idx = {r["id"]: idx for idx, r in enumerate(reports)}

    indices = geo.within(center, report_points, radius_m=400.0)

    idx_r012 = id_to_idx["r012"]
    idx_r013 = id_to_idx["r013"]
    idx_r001 = id_to_idx["r001"]

    assert idx_r012 in indices
    assert idx_r013 in indices
    assert idx_r001 not in indices


def test_criterion_3_distance_to_polyline_point_on_line() -> None:
    """Критерий 3: distance_to_polyline_m для точки на линии = 0 ± 1 м."""
    line = [
        GeoPoint(lat=47.010, lon=28.840),
        GeoPoint(lat=47.020, lon=28.840),
        GeoPoint(lat=47.020, lon=28.850),
    ]

    # Точка точно посередине первого сегмента
    point_on_segment_1 = GeoPoint(lat=47.015, lon=28.840)
    dist, along = geo.distance_to_polyline_m(point_on_segment_1, line)
    assert abs(dist) <= 1.0, f"Expected dist <= 1m, got {dist}m"
    seg_1_len = geo.haversine_m(line[0], line[1])
    assert abs(along - seg_1_len / 2.0) <= 2.0

    # Точка в вершине линии
    vertex = line[1]
    dist_v, along_v = geo.distance_to_polyline_m(vertex, line)
    assert abs(dist_v) <= 1.0
    assert abs(along_v - seg_1_len) <= 2.0


def test_criterion_4_geocode_returns_none_when_off() -> None:
    """Критерий 4: При GEOCODER=off или ошибке сети geocode возвращает None без исключения."""
    result = geo.geocode("str. Alexei Mateevici 85, Chișinău")
    assert result is None


# ==============================================================================
# 2. Тесты функций centroid и h3_cell
# ==============================================================================


def test_centroid_calculation() -> None:
    """Проверка вычисления центроида для нескольких точек."""
    p1 = GeoPoint(lat=47.0, lon=28.0)
    p2 = GeoPoint(lat=47.2, lon=28.4)
    c = geo.centroid([p1, p2])
    assert abs(c.lat - 47.1) < 1e-6
    assert abs(c.lon - 28.2) < 1e-6

    # 1 точка
    c_single = geo.centroid([p1])
    assert c_single.lat == 47.0
    assert c_single.lon == 28.0

    # Пустой список бросает ValueError
    with pytest.raises(ValueError, match="points cannot be empty"):
        geo.centroid([])


def test_h3_cell_deterministic_rounding() -> None:
    """h3_cell в L0 детерминированно возвращает строку округлённых координат."""
    p = GeoPoint(lat=47.018225, lon=28.842198)
    cell = geo.h3_cell(p, res=9)
    assert isinstance(cell, str)
    assert "47.0182" in cell
    assert "28.8422" in cell
    assert cell == geo.h3_cell(p, res=9)


# ==============================================================================
# 3. QA Чеклист: границы данных, откат на L0, детерминированность
# ==============================================================================


def test_qa_determinism() -> None:
    """QA 5: Детерминированность: повторные вызовы дают идентичный результат."""
    a = GeoPoint(lat=47.018, lon=28.842)
    b = GeoPoint(lat=47.033, lon=28.840)
    assert geo.haversine_m(a, b) == geo.haversine_m(a, b)

    line = [a, b]
    assert geo.distance_to_polyline_m(a, line) == geo.distance_to_polyline_m(a, line)
    assert geo.centroid(line) == geo.centroid(line)
    assert geo.within(a, line, 1000.0) == geo.within(a, line, 1000.0)


def test_qa_data_boundaries() -> None:
    """QA 3: Границы данных: нулевые расстояния, пустые списки, одинаковые точки, полюса."""
    # Одинаковые точки
    p = GeoPoint(lat=47.0, lon=28.0)
    assert geo.haversine_m(p, p) == 0.0

    # Пустая полилиния
    assert geo.distance_to_polyline_m(p, []) == (0.0, 0.0)

    # Полилиния из 1 точки
    dist, along = geo.distance_to_polyline_m(p, [p])
    assert dist == 0.0
    assert along == 0.0

    # Пустой список points в within
    assert geo.within(p, [], 500.0) == []

    # Полюса и антимеридиан
    north = GeoPoint(lat=90.0, lon=0.0)
    south = GeoPoint(lat=-90.0, lon=0.0)
    dist_ns = geo.haversine_m(north, south)
    # Половина окружности Земли ~ 20015 км (20_015_000 м)
    assert 20_000_000.0 <= dist_ns <= 20_030_000.0


def test_qa_fallback_to_l0_on_l1_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """QA 4: Ошибка L1 перехватывается, пишется warning, возвращается результат L0."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    monkeypatch.setattr(settings, "GEOCODER", "nominatim")

    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("Geocode L1 failed")

    monkeypatch.setattr(geo.l1, "geocode", boom)
    monkeypatch.setattr(geo.l1, "h3_cell", boom)

    # geocode должен тихо вернуть None
    assert geo.geocode("some address") is None

    # h3_cell должен тихо вернуть результат l0
    p = GeoPoint(lat=47.0, lon=28.0)
    assert geo.h3_cell(p) == geo.l0.h3_cell(p)
