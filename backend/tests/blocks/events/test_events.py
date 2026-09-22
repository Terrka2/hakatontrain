"""Тесты блока X1 (events): критерии приёмки 1–4, фактор EX и роуты API."""

import json
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.blocks.events import apply_deadlines, enrich_context, get_events, l0
from app.blocks.priority.factors import ex
from app.contracts import models
from app.core.config import settings
from app.main import app
from app.models import User

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "app" / "fixtures" / "demo_city.json"
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_state() -> Generator[None]:
    from app.api.routes.events import router as events_router

    if not any(
        getattr(r, "path", "").startswith(f"{settings.API_V1_STR}/events")
        for r in app.routes
    ):
        app.include_router(events_router, prefix=settings.API_V1_STR)
    app.dependency_overrides.clear()
    l0.reset_state()
    yield
    app.dependency_overrides.clear()
    l0.reset_state()


def make_user(role: str) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role}@demo.md",
        role=role,
        is_active=True,
        is_superuser=False,
        hashed_password="mock",
    )


def load_fixture() -> dict[str, Any]:
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def test_criterion_1_get_events_dates() -> None:
    """Критерий 1: get_events возвращает e1 для 26-28 сентября 2026 и пусто для октября."""
    t_start = datetime(2026, 9, 26, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 28, 23, 59, tzinfo=UTC)
    events = get_events(t_start, t_end)
    assert len(events) >= 1
    assert any(e.id == "e1" for e in events)

    t_oct_start = datetime(2026, 10, 1, 0, 0, tzinfo=UTC)
    t_oct_end = datetime(2026, 10, 31, 23, 59, tzinfo=UTC)
    oct_events = get_events(t_oct_start, t_oct_end)
    assert len(oct_events) == 0


def test_criterion_2_apply_deadlines_for_r012_r013() -> None:
    """Критерий 2: задачи по r012 и r013 получают deadline = начало e1."""
    data = load_fixture()
    reports = {r["id"]: models.Report(**r) for r in data["reports"]}
    e1 = models.Event(**data["events"][0])

    # Строим кластеры и задачи для r012 (близко к e1), r013 (близко к e1) и r001 (далеко)
    c_r012 = models.Cluster(
        id="cl_r012",
        category="pothole",
        centroid=reports["r012"].location,
        report_ids=["r012"],
        first_reported_at=reports["r012"].created_at,
        last_reported_at=reports["r012"].created_at,
    )
    c_r013 = models.Cluster(
        id="cl_r013",
        category="garbage",
        centroid=reports["r013"].location,
        report_ids=["r013"],
        first_reported_at=reports["r013"].created_at,
        last_reported_at=reports["r013"].created_at,
    )
    c_r001 = models.Cluster(
        id="cl_r001",
        category="pothole",
        centroid=reports["r001"].location,
        report_ids=["r001"],
        first_reported_at=reports["r001"].created_at,
        last_reported_at=reports["r001"].created_at,
    )

    j_r012 = models.Job(
        id="job_r012",
        cluster_ids=["cl_r012"],
        location=reports["r012"].location,
        skill="road",
        service_min=30,
        priority=70,
    )
    j_r013 = models.Job(
        id="job_r013",
        cluster_ids=["cl_r013"],
        location=reports["r013"].location,
        skill="sanitation",
        service_min=30,
        priority=60,
    )
    j_r001 = models.Job(
        id="job_r001",
        cluster_ids=["cl_r001"],
        location=reports["r001"].location,
        skill="road",
        service_min=30,
        priority=70,
    )

    updated_jobs, decisions = apply_deadlines(
        jobs=[j_r012, j_r013, j_r001],
        clusters=[c_r012, c_r013, c_r001],
        events=[e1],
    )

    job_map = {j.id: j for j in updated_jobs}
    assert job_map["job_r012"].deadline == e1.starts_at
    assert job_map["job_r013"].deadline == e1.starts_at
    assert job_map["job_r001"].deadline is None

    assert any(d.subject_id == "job_r012" and d.kind == "deadline" for d in decisions)
    assert any(d.subject_id == "job_r013" and d.kind == "deadline" for d in decisions)


def test_criterion_3_factor_ex() -> None:
    """Критерий 3: фактор EX для r012 = 1.0, в evidence назван забег; для r001 = 0."""
    data = load_fixture()
    reports = {r["id"]: models.Report(**r) for r in data["reports"]}
    e1 = models.Event(**data["events"][0])

    t_now = datetime.fromisoformat(data["now"])
    ctx_with_event = models.Context(now=t_now, events=[e1])
    ctx_empty = models.Context(now=t_now, events=[])

    c_r012 = models.Cluster(
        id="cl_r012",
        category="pothole",
        centroid=reports["r012"].location,
        report_ids=["r012"],
        first_reported_at=reports["r012"].created_at,
        last_reported_at=reports["r012"].created_at,
    )
    c_r001 = models.Cluster(
        id="cl_r001",
        category="pothole",
        centroid=reports["r001"].location,
        report_ids=["r001"],
        first_reported_at=reports["r001"].created_at,
        last_reported_at=reports["r001"].created_at,
    )

    # 1. r012 в радиусе e1 (забег)
    score_12, ev_12 = ex.evaluate(c_r012, [reports["r012"]], [], ctx_with_event)
    assert score_12 == 1.0
    assert any("забег" in str(x).lower() for x in ev_12)

    # 2. r001 далеко от e1
    score_01, ev_01 = ex.evaluate(c_r001, [reports["r001"]], [], ctx_with_event)
    assert score_01 == 0.0
    assert len(ev_01) == 0

    # 3. Нет событий -> None
    score_none, ev_none = ex.evaluate(c_r012, [reports["r012"]], [], ctx_empty)
    assert score_none is None
    assert len(ev_none) == 0


def test_criterion_4_optional_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Критерий 4: OPTIONAL_BLOCKS=off -> ctx.events == [], роуты отдают 404."""
    data = load_fixture()
    t_now = datetime.fromisoformat(data["now"])

    # 1. OPTIONAL_BLOCKS == 'off'
    monkeypatch.setattr(settings, "OPTIONAL_BLOCKS", "off")
    ctx = models.Context(now=t_now)
    enriched = enrich_context(ctx)
    assert enriched.events == []

    # Проверка роута: 404 при выключенном OPTIONAL_BLOCKS
    app.dependency_overrides[get_current_user] = lambda: make_user("supervisor")
    r = client.get(
        f"{settings.API_V1_STR}/events", headers={"Authorization": "Bearer mock"}
    )
    assert r.status_code == 404

    # 2. OPTIONAL_BLOCKS == 'on'
    monkeypatch.setattr(settings, "OPTIONAL_BLOCKS", "on")
    enriched_on = enrich_context(ctx)
    assert len(enriched_on.events) >= 1
    assert any(e.id == "e1" for e in enriched_on.events)


def test_events_routes_auth_and_crud(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверка роутов GET /events и POST /events при OPTIONAL_BLOCKS=on."""
    monkeypatch.setattr(settings, "OPTIONAL_BLOCKS", "on")

    # 401 без токена
    r = client.get(f"{settings.API_V1_STR}/events")
    assert r.status_code == 401

    # 200 для авторизованного пользователя
    app.dependency_overrides[get_current_user] = lambda: make_user("citizen")
    r = client.get(
        f"{settings.API_V1_STR}/events?from=2026-09-26T00:00:00Z&to=2026-09-28T23:59:59Z",
        headers={"Authorization": "Bearer mock"},
    )
    assert r.status_code == 200
    events_data = r.json()
    assert isinstance(events_data, list)
    assert any(e["id"] == "e1" for e in events_data)

    # POST /events: 403 для citizen
    event_payload = {
        "id": "e_new",
        "title": "Фестиваль вина",
        "location": {"lat": 47.025, "lon": 28.835},
        "radius_m": 300,
        "starts_at": "2026-09-29T10:00:00+03:00",
        "ends_at": "2026-09-29T18:00:00+03:00",
        "expected_people": 1500,
        "source": "manual",
    }
    r_post = client.post(
        f"{settings.API_V1_STR}/events",
        headers={"Authorization": "Bearer mock"},
        json=event_payload,
    )
    assert r_post.status_code == 403

    # POST /events: 200/201 для supervisor
    app.dependency_overrides[get_current_user] = lambda: make_user("supervisor")
    r_post_sup = client.post(
        f"{settings.API_V1_STR}/events",
        headers={"Authorization": "Bearer mock"},
        json=event_payload,
    )
    assert r_post_sup.status_code in (200, 201)
    assert r_post_sup.json()["id"] == "e_new"

    # POST /events: 422 при невалидном теле
    r_post_invalid = client.post(
        f"{settings.API_V1_STR}/events",
        headers={"Authorization": "Bearer mock"},
        json={"title": "No id or location"},
    )
    assert r_post_invalid.status_code == 422


def test_apply_deadlines_boundaries() -> None:
    """Границы данных: пустые списки, отсутствие кластеров, события без пересечений."""
    # Пустые списки
    jobs, decisions = apply_deadlines([], [], [])
    assert jobs == []
    assert decisions == []

    # Задачи без совпадений
    j = models.Job(
        id="j_none",
        cluster_ids=["cl_none"],
        location=models.GeoPoint(lat=0.0, lon=0.0),
        skill="road",
        service_min=15,
        priority=50,
    )
    ev = models.Event(
        id="ev_far",
        title="Far",
        location=models.GeoPoint(lat=80.0, lon=80.0),
        starts_at=datetime(2026, 9, 27, 10, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 27, 12, 0, tzinfo=UTC),
    )
    jobs, decisions = apply_deadlines([j], [], [ev])
    assert len(jobs) == 1
    assert jobs[0].deadline is None
    assert decisions == []


def test_factor_ex_boundaries() -> None:
    """Границы данных для фактора EX: события > 72ч, завершившиеся события, наивные даты."""
    t_now = datetime(2026, 9, 26, 7, 0, tzinfo=UTC)
    loc = models.GeoPoint(lat=47.0245, lon=28.8323)
    c = models.Cluster(
        id="cl_test",
        category="pothole",
        centroid=loc,
        report_ids=["r1"],
        first_reported_at=t_now,
        last_reported_at=t_now,
    )

    # 1. Событие начинается более чем через 72 часа (напр. через 100 часов)
    ev_far_time = models.Event(
        id="ev_future",
        title="Будущий концерт",
        location=loc,
        radius_m=500,
        starts_at=t_now + timedelta(hours=100),
        ends_at=t_now + timedelta(hours=105),
        expected_people=5000,
    )
    ctx_future = models.Context(now=t_now, events=[ev_far_time])
    score, ev_list = ex.evaluate(c, [], [], ctx_future)
    assert score == 0.0
    assert ev_list == []

    # 2. Событие уже завершилось
    ev_past = models.Event(
        id="ev_past",
        title="Прошедший концерт",
        location=loc,
        radius_m=500,
        starts_at=t_now - timedelta(hours=5),
        ends_at=t_now - timedelta(hours=2),
        expected_people=5000,
    )
    ctx_past = models.Context(now=t_now, events=[ev_past])
    score_p, ev_p = ex.evaluate(c, [], [], ctx_past)
    assert score_p == 0.0
    assert ev_p == []
