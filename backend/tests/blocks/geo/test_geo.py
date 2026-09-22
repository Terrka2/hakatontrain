"""Тесты блока B2 (geo).

Один критерий приёмки = минимум один тест.
Все тесты проходят БЕЗ сети и БЕЗ базы данных.
"""

import json
from collections.abc import Generator
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
def disable_network(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Запрещает любые сетевые вызовы в тестах блока и очищает кэш геокодера."""
    geo.l1.clear_cache()

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("Network access forbidden in block tests")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("socket.socket.connect", forbidden)
    yield
    geo.l1.clear_cache()


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


def test_criterion_2_within(fixture_data: dict[str, Any]) -> None:
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

    # Пустая полилиния бросает ValueError("Empty line")
    with pytest.raises(ValueError, match="Empty line"):
        geo.distance_to_polyline_m(p, [])

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


# ==============================================================================
# 4. Тесты уровня L1 (geopy Nominatim, кэш, ограничение Кишинёва, h3)
# ==============================================================================


class MockLocation:
    def __init__(self, lat: float, lon: float) -> None:
        self.latitude = lat
        self.longitude = lon


def test_l1_geocode_chisinau_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """L1: успешное геокодирование адреса в Кишинёве через Nominatim с country_codes='md'."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    monkeypatch.setattr(settings, "GEOCODER", "nominatim")

    def mock_geocode(_self: Any, query: str, **kwargs: Any) -> Any:
        assert kwargs.get("country_codes") == "md"
        if "Mateevici" in query:
            return MockLocation(47.0182, 28.8422)
        return None

    monkeypatch.setattr("geopy.geocoders.Nominatim.geocode", mock_geocode)

    res = geo.geocode("str. Alexei Mateevici 85, Chișinău")
    assert res is not None
    assert res.lat == 47.0182
    assert res.lon == 28.8422


def test_l1_geocode_outside_chisinau_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """L1: адреса за пределами bounding box Кишинёва возвращают None."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    monkeypatch.setattr(settings, "GEOCODER", "nominatim")

    def mock_geocode(_self: Any, _query: str, **kwargs: Any) -> Any:
        assert kwargs.get("country_codes") == "md"
        return MockLocation(51.5074, -0.1278)

    monkeypatch.setattr("geopy.geocoders.Nominatim.geocode", mock_geocode)

    res = geo.geocode("Baker Street 221B, London")
    assert res is None


def test_l1_geocode_not_found_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """L1: если адрес не найден Nominatim — возвращается None без исключения."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    monkeypatch.setattr(settings, "GEOCODER", "nominatim")

    monkeypatch.setattr(
        "geopy.geocoders.Nominatim.geocode", lambda _self, _q, **kw: None
    )

    res = geo.geocode("Nonexistent Street 999")
    assert res is None


def test_l1_geocode_network_or_timeout_error_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """L1: ошибка сети или таймаут пробрасывается из l1.py и перехватывается в __init__.py с откатом на L0."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    monkeypatch.setattr(settings, "GEOCODER", "nominatim")

    def mock_fail(_self: Any, _q: str, **_kwargs: Any) -> Any:
        raise TimeoutError("Nominatim request timed out")

    monkeypatch.setattr("geopy.geocoders.Nominatim.geocode", mock_fail)

    # 1. l1.geocode напрямую пробрасывает исключение без внутреннего try/except
    with pytest.raises(TimeoutError, match="timed out"):
        geo.l1.geocode("str. Pushkin 10, Chișinău")

    # 2. geo.geocode (порт в __init__.py) ловит исключение, логирует и возвращает L0 (None)
    res = geo.geocode("str. Pushkin 10, Chișinău")
    assert res is None


def test_l1_geocode_in_memory_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """L1: повторные запросы к одному адресу возвращаются из кэша без вызова Nominatim."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    monkeypatch.setattr(settings, "GEOCODER", "nominatim")

    calls = 0

    def mock_geocode(_self: Any, _query: str, **_kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        return MockLocation(47.0205, 28.8350)

    monkeypatch.setattr("geopy.geocoders.Nominatim.geocode", mock_geocode)

    addr = "bd. Stefan cel Mare 1, Chisinau"
    p1 = geo.geocode(addr)
    assert p1 is not None
    assert calls == 1

    p2 = geo.geocode(addr)
    assert p2 is not None
    assert p2.lat == p1.lat
    assert p2.lon == p1.lon
    assert calls == 1


def test_l1_h3_cell_library() -> None:
    """L1: h3_cell возвращает валидный строковый идентификатор ячейки H3."""
    p = GeoPoint(lat=47.0182, lon=28.8422)
    cell = geo.l1.h3_cell(p, res=9)
    assert isinstance(cell, str)
    assert len(cell) == 15
    assert cell == geo.l1.h3_cell(p, res=9)


def test_l1_geocoder_off_and_mock_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверка переключателей GEOCODER=off и USE_MOCK=true."""
    # При GEOCODER=off -> всегда L0 (None)
    monkeypatch.setattr(settings, "USE_MOCK", False)
    monkeypatch.setattr(settings, "GEOCODER", "off")
    assert geo.geocode("str. Alexei Mateevici 85") is None

    # При USE_MOCK=true -> L0
    monkeypatch.setattr(settings, "USE_MOCK", True)
    monkeypatch.setattr(settings, "GEOCODER", "nominatim")
    assert geo.geocode("str. Alexei Mateevici 85") is None

    p = GeoPoint(lat=47.0182, lon=28.8422)
    h3_l0 = geo.h3_cell(p, res=9)
    assert "47.0182" in h3_l0


def test_l1_empty_and_whitespace_address() -> None:
    """L1: пустые строки или строки из пробелов возвращают None без запросов."""
    assert geo.l1.geocode("") is None
    assert geo.l1.geocode("   ") is None
