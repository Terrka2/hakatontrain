"""Тесты уровня L1 блока X1: интеграция с репозиторием D1, ручной ввод и откат на L0."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import app.blocks.events as events
from app.api.deps import get_current_user
from app.blocks.events import l0, l1
from app.contracts import models
from app.core.config import settings
from app.db import get_repository
from app.main import app
from app.models import User

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    from app.api.routes.events import router as events_router

    if not any(
        getattr(r, "path", "").startswith(f"{settings.API_V1_STR}/events")
        for r in app.routes
    ):
        app.include_router(events_router, prefix=settings.API_V1_STR)
    app.dependency_overrides.clear()
    l0.reset_state()
    monkeypatch.setattr(
        "app.blocks.events.l2.fetch_external_events", lambda *_a, **_kw: []
    )
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


def sample_event() -> models.Event:
    return models.Event(
        id="e_test",
        title="Тестовый марафон",
        location=models.GeoPoint(lat=47.025, lon=28.835),
        radius_m=350,
        starts_at=datetime(2026, 9, 28, 9, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 28, 14, 0, tzinfo=UTC),
        expected_people=1200,
        source="manual",
    )


def test_l1_get_events_and_add_event_mock_repo() -> None:
    """Проверка прямых функций l1.get_events и l1.add_event с объектом repo."""
    repo = MagicMock()
    ev = sample_event()
    t_start = datetime(2026, 9, 28, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 28, 23, 59, tzinfo=UTC)

    repo.list_events.return_value = [ev]
    repo.add_event.return_value = ev

    res = l1.get_events(t_start, t_end, repo=repo)
    assert len(res) == 1
    assert res[0].id == "e_test"
    repo.list_events.assert_called_once_with(t_start, t_end)

    saved = l1.add_event(ev, repo=repo)
    assert saved.id == "e_test"
    repo.add_event.assert_called_once_with(ev)


def test_fallback_to_l0_when_d1_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """При исключении D1 порт тихо откатывается на L0 с записью в лог."""
    monkeypatch.setattr(settings, "USE_MOCK", False)

    def raise_db_err(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("Database connection failed")

    monkeypatch.setattr(l1, "get_events", raise_db_err)
    monkeypatch.setattr(l1, "add_event", raise_db_err)

    t_start = datetime(2026, 9, 26, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 28, 23, 59, tzinfo=UTC)

    # 1. get_events откат на фикстуру L0 (событие e1)
    with caplog.at_level("WARNING"):
        res = events.get_events(t_start, t_end)
    assert any(e.id == "e1" for e in res)
    assert "X1: L1 get_events failed, falling back to L0" in caplog.text

    # 2. add_event откат на L0
    ev = sample_event()
    with caplog.at_level("WARNING"):
        saved = events.add_event(ev)
    assert saved.id == "e_test"
    assert "X1: L1 add_event failed, falling back to L0" in caplog.text


def test_use_mock_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    """При settings.USE_MOCK=True вызов идёт строго в L0 без попыток L1."""
    monkeypatch.setattr(settings, "USE_MOCK", True)
    l1_mock = MagicMock()
    monkeypatch.setattr(l1, "get_events", l1_mock)

    t_start = datetime(2026, 9, 26, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 28, 23, 59, tzinfo=UTC)
    res = events.get_events(t_start, t_end)

    assert any(e.id == "e1" for e in res)
    l1_mock.assert_not_called()


def test_routes_l1_with_mock_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверка роутов GET /events и POST /events через инъекцию мока get_repository."""
    monkeypatch.setattr(settings, "OPTIONAL_BLOCKS", "on")
    monkeypatch.setattr(settings, "USE_MOCK", False)

    mock_repo = MagicMock()
    ev = sample_event()
    mock_repo.list_events.return_value = [ev]
    mock_repo.add_event.return_value = ev

    app.dependency_overrides[get_repository] = lambda: mock_repo
    app.dependency_overrides[get_current_user] = lambda: make_user("supervisor")

    # GET /events
    r_get = client.get(
        f"{settings.API_V1_STR}/events?from=2026-09-28T00:00:00Z&to=2026-09-28T23:59:59Z",
        headers={"Authorization": "Bearer mock"},
    )
    assert r_get.status_code == 200
    data = r_get.json()
    assert len(data) == 1
    assert data[0]["id"] == "e_test"
    mock_repo.list_events.assert_called()

    # POST /events
    r_post = client.post(
        f"{settings.API_V1_STR}/events",
        headers={"Authorization": "Bearer mock"},
        json=ev.model_dump(mode="json"),
    )
    assert r_post.status_code in (200, 201)
    assert r_post.json()["id"] == "e_test"
    mock_repo.add_event.assert_called()


def test_routes_fallback_on_repo_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """При ошибке D1 в роутах происходит откат на L0 (возврат e1)."""
    monkeypatch.setattr(settings, "OPTIONAL_BLOCKS", "on")
    monkeypatch.setattr(settings, "USE_MOCK", False)

    err_repo = MagicMock()
    err_repo.list_events.side_effect = RuntimeError("DB down")

    app.dependency_overrides[get_repository] = lambda: err_repo
    app.dependency_overrides[get_current_user] = lambda: make_user("citizen")

    with caplog.at_level("WARNING"):
        r_get = client.get(
            f"{settings.API_V1_STR}/events?from=2026-09-26T00:00:00Z&to=2026-09-28T23:59:59Z",
            headers={"Authorization": "Bearer mock"},
        )
    assert r_get.status_code == 200
    data = r_get.json()
    assert any(e["id"] == "e1" for e in data)
    assert "X1: L1 get_events failed, falling back to L0" in caplog.text
