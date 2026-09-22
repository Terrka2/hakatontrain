"""Тесты блока B5 (context): сбор погоды, инфраструктуры и правила погоды."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.blocks import context
from app.contracts.models import GeoPoint, Job, Weather
from app.core.config import settings

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "app" / "fixtures" / "demo_city.json"
)


@pytest.fixture(autouse=True)
def _reset_context_state() -> None:
    context.reset_scenario()
    context.clear_cache()


@pytest.fixture(scope="module")
def fixture_data() -> dict:
    with FIXTURE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_jobs() -> list[Job]:
    # r001: pothole, r014: tree, r004: streetlight
    return [
        Job(
            id="j_pothole",
            cluster_ids=["r001"],
            location=GeoPoint(lat=47.018, lon=28.842),
            skill="road",
            service_min=45,
            priority=50,
        ),
        Job(
            id="j_tree",
            cluster_ids=["r014"],
            location=GeoPoint(lat=47.02, lon=28.85),
            skill="green",
            service_min=60,
            priority=40,
        ),
        Job(
            id="j_light",
            cluster_ids=["r004"],
            location=GeoPoint(lat=47.018, lon=28.841),
            skill="electric",
            service_min=30,
            priority=30,
        ),
    ]


def test_criterion_1_storm_defers_pothole_and_boosts_tree(
    sample_jobs: list[Job], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Критерий 1: fixture:storm -> apply_weather_rules откладывает pothole и поднимает priority tree."""
    monkeypatch.setattr(settings, "WEATHER", "fixture:storm")
    weather = context.get_weather(GeoPoint(lat=47.018, lon=28.842), datetime.now(UTC))
    assert weather is not None
    assert weather.precipitation_mm >= 5.0
    assert weather.wind_ms >= 15.0

    kept_jobs, decisions = context.apply_weather_rules(sample_jobs, weather)

    # pothole отложен -> убран из списка
    kept_ids = [j.id for j in kept_jobs]
    assert "j_pothole" not in kept_ids
    assert "j_tree" in kept_ids
    assert "j_light" in kept_ids

    # tree получил +20 приоритета (40 -> 60)
    tree_job = next(j for j in kept_jobs if j.id == "j_tree")
    assert tree_job.priority == 60

    # light получил service_min * 1.3 (30 -> 39)
    light_job = next(j for j in kept_jobs if j.id == "j_light")
    assert light_job.service_min == 39

    # Для каждого изменения есть Decision с русской причиной
    defer_decisions = [
        d for d in decisions if d.kind == "defer" and d.subject_id == "j_pothole"
    ]
    assert len(defer_decisions) == 1
    assert any(
        "осадки" in d.reason.lower() or "отложен" in d.reason.lower()
        for d in defer_decisions
    )

    boost_decisions = [
        d for d in decisions if d.kind == "boost" and d.subject_id == "j_tree"
    ]
    assert len(boost_decisions) == 1
    assert any(
        "ветер" in d.reason.lower() or "приоритет" in d.reason.lower()
        for d in boost_decisions
    )


def test_criterion_2_clear_does_not_change_jobs(
    sample_jobs: list[Job], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Критерий 2: fixture:clear -> список задач не меняется, decisions == []."""
    monkeypatch.setattr(settings, "WEATHER", "fixture:clear")
    weather = context.get_weather(GeoPoint(lat=47.018, lon=28.842), datetime.now(UTC))
    assert weather is not None
    assert weather.precipitation_mm == 0.0

    kept_jobs, decisions = context.apply_weather_rules(sample_jobs, weather)
    assert kept_jobs == sample_jobs
    assert decisions == []


def test_criterion_3_weather_none_does_not_change_jobs(sample_jobs: list[Job]) -> None:
    """Критерий 3: weather=None -> задачи не меняются, исключений нет, decisions == []."""
    kept_jobs, decisions = context.apply_weather_rules(sample_jobs, None)
    assert kept_jobs == sample_jobs
    assert decisions == []


def test_criterion_4_open_meteo_timeout_falls_back_to_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Критерий 4: Open-Meteo недоступен (мок таймаута) -> возвращается fixture-погода, source='fixture'."""
    monkeypatch.setattr(settings, "WEATHER", "open-meteo")

    def mock_get(*_args: object, **_kwargs: object) -> None:
        raise httpx.TimeoutException("Open-Meteo timed out")

    monkeypatch.setattr(httpx.Client, "get", mock_get)

    weather = context.get_weather(GeoPoint(lat=47.018, lon=28.842), datetime.now(UTC))
    assert weather is not None
    assert weather.source == "fixture"


def test_criterion_5_build_context_returns_3_infra_and_empty_events() -> None:
    """Критерий 5: build_context возвращает 3 объекта инфраструктуры и events == []."""
    now = datetime(2026, 9, 26, 7, 0, tzinfo=UTC)
    ctx = context.build_context(now)

    assert ctx.now == now
    assert ctx.events == []
    assert len(ctx.infrastructure) == 3
    infra_ids = {obj.id for obj in ctx.infrastructure}
    assert infra_ids == {"s1", "k1", "h1"}


def test_determinism(sample_jobs: list[Job]) -> None:
    """Детерминированность: два вызова подряд дают строго одинаковый результат."""
    now = datetime(2026, 9, 26, 7, 0, tzinfo=UTC)
    ctx1 = context.build_context(now)
    ctx2 = context.build_context(now)
    assert ctx1 == ctx2

    weather = context.get_weather(GeoPoint(lat=47.018, lon=28.842), now)
    res1 = context.apply_weather_rules(sample_jobs, weather)
    res2 = context.apply_weather_rules(sample_jobs, weather)
    assert res1 == res2


def test_boundary_and_edge_cases() -> None:
    """Граничные условия: пустой список, один элемент, приоритет близкий к 100."""
    # Пустой список
    kept, decisions = context.apply_weather_rules(
        [],
        Weather(
            at=datetime.now(UTC),
            precipitation_mm=20,
            wind_ms=25,
            temp_c=10,
            source="fixture",
        ),
    )
    assert kept == []
    assert decisions == []

    # Приоритет близкий к 100 не превышает 100 при boost
    job_tree_high = Job(
        id="j_tree_max",
        cluster_ids=["tree_cluster"],
        location=GeoPoint(lat=47.0, lon=28.0),
        skill="green",
        service_min=60,
        priority=95,
    )
    kept, _ = context.apply_weather_rules(
        [job_tree_high],
        Weather(
            at=datetime.now(UTC),
            precipitation_mm=0,
            wind_ms=20,
            temp_c=10,
            source="fixture",
        ),
    )
    assert kept[0].priority == 100


def test_no_network_allowed(
    monkeypatch: pytest.MonkeyPatch, sample_jobs: list[Job]
) -> None:
    """Проверка работы без сети: любой реальный вызов по сети блокируется."""

    def forbidden_network(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("No network calls allowed in tests!")

    monkeypatch.setattr(httpx.Client, "get", forbidden_network)
    ctx = context.build_context(datetime.now(UTC))
    assert ctx is not None
    kept, _ = context.apply_weather_rules(sample_jobs, ctx.weather)
    assert len(kept) == len(sample_jobs)


def test_l1_open_meteo_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """L1: Open-Meteo возвращает Weather с source='open-meteo' при 200 OK."""
    monkeypatch.setattr(settings, "WEATHER", "open-meteo")

    def mock_get(*_args: object, **_kwargs: object) -> httpx.Response:
        content = json.dumps(
            {
                "current": {
                    "precipitation": 2.5,
                    "wind_speed_10m": 8.0,
                    "temperature_2m": 19.5,
                }
            }
        ).encode("utf-8")
        return httpx.Response(
            200,
            content=content,
            request=httpx.Request("GET", "https://api.open-meteo.com"),
        )

    monkeypatch.setattr(httpx.Client, "get", mock_get)
    point = GeoPoint(lat=47.018, lon=28.842)
    at = datetime(2026, 9, 26, 8, 0, tzinfo=UTC)
    weather = context.get_weather(point, at)
    assert weather is not None
    assert weather.source == "open-meteo"
    assert weather.precipitation_mm == 2.5
    assert weather.wind_ms == 8.0
    assert weather.temp_c == 19.5


def test_l1_open_meteo_error_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """L1: При ошибке подключения происходит тихий откат на fixture."""
    monkeypatch.setattr(settings, "WEATHER", "open-meteo")

    def mock_get(*_args: object, **_kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx.Client, "get", mock_get)
    weather = context.get_weather(GeoPoint(lat=47.018, lon=28.842), datetime.now(UTC))
    assert weather is not None
    assert weather.source == "fixture"


def test_l1_cache_hit_avoids_http_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """L1: Повторный запрос в пределах 30 минут берётся из кэша без нового HTTP-вызова."""
    monkeypatch.setattr(settings, "WEATHER", "open-meteo")
    calls = 0

    def mock_get(*_args: object, **_kwargs: object) -> httpx.Response:
        nonlocal calls
        calls += 1
        content = json.dumps(
            {
                "current": {
                    "precipitation": 1.0,
                    "wind_speed_10m": 5.0,
                    "temperature_2m": 20.0,
                }
            }
        ).encode("utf-8")
        return httpx.Response(
            200,
            content=content,
            request=httpx.Request("GET", "https://api.open-meteo.com"),
        )

    monkeypatch.setattr(httpx.Client, "get", mock_get)
    point = GeoPoint(lat=47.018, lon=28.842)
    w1 = context.get_weather(point, datetime.now(UTC))
    assert calls == 1
    assert w1 is not None and w1.source == "open-meteo"

    # Второй вызов с теми же координатами не делает повторный запрос
    w2 = context.get_weather(point, datetime.now(UTC))
    assert calls == 1
    assert w2 is not None and w2.source == "open-meteo"
    assert w1.precipitation_mm == w2.precipitation_mm

    # Вызов с другими координатами делает новый запрос
    point_other = GeoPoint(lat=47.050, lon=28.890)
    w3 = context.get_weather(point_other, datetime.now(UTC))
    assert calls == 2
    assert w3 is not None and w3.source == "open-meteo"
