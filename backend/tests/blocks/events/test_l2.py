"""Тесты уровня L2 блока X1: внешний API источник, обработка таймаутов и каскадный откат."""

import json
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

import app.blocks.events as events
from app.api.deps import get_current_user
from app.blocks.events import l0, l2
from app.contracts import models
from app.core.config import settings
from app.main import app
from app.models import User

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


def sample_external_event() -> models.Event:
    return models.Event(
        id="e_ext_1",
        title="Городской полумарафон",
        location=models.GeoPoint(lat=47.027, lon=28.832),
        radius_m=400,
        starts_at=datetime(2026, 9, 27, 8, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 27, 13, 0, tzinfo=UTC),
        expected_people=2500,
        source="events.demo-city.local",
    )


def test_l2_fetch_external_events_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """1. fetch_external_events успешно парсит ответ внешнего API в модели Event."""
    ev = sample_external_event()
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = [ev.model_dump(mode="json")]

    def mock_get(*_args: object, **_kwargs: object) -> MagicMock:
        return mock_resp

    monkeypatch.setattr(httpx.Client, "get", mock_get)

    t_start = datetime(2026, 9, 27, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 27, 23, 59, tzinfo=UTC)
    res = l2.fetch_external_events(t_start, t_end)
    assert len(res) == 1
    assert res[0].id == "e_ext_1"
    assert res[0].title == "Городской полумарафон"


def test_l2_fetch_external_events_dict_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2. Поддержка формата {'events': [...]} во внешнем API."""
    ev = sample_external_event()
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"events": [ev.model_dump(mode="json")]}

    monkeypatch.setattr(httpx.Client, "get", lambda *_a, **_kw: mock_resp)

    t_start = datetime(2026, 9, 27, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 27, 23, 59, tzinfo=UTC)
    res = l2.fetch_external_events(t_start, t_end)
    assert len(res) == 1
    assert res[0].id == "e_ext_1"


def test_l2_fetch_external_events_timeout(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """3. При таймауте сети fetch_external_events логирует warning и возвращает []."""

    def mock_timeout(*_args: object, **_kwargs: object) -> None:
        raise httpx.ReadTimeout("Request timed out", request=MagicMock())

    monkeypatch.setattr(httpx.Client, "get", mock_timeout)

    t_start = datetime(2026, 9, 27, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 27, 23, 59, tzinfo=UTC)
    with caplog.at_level("WARNING"):
        res = l2.fetch_external_events(t_start, t_end)

    assert res == []
    assert "X1 L2 external API failed" in caplog.text


def test_l2_fetch_external_events_invalid_json(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """4. При невалидном JSON от API возвращается [] без падения."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.side_effect = json.JSONDecodeError("Invalid JSON", "bad string", 0)

    monkeypatch.setattr(httpx.Client, "get", lambda *_a, **_kw: mock_resp)

    t_start = datetime(2026, 9, 27, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 27, 23, 59, tzinfo=UTC)
    with caplog.at_level("WARNING"):
        res = l2.fetch_external_events(t_start, t_end)

    assert res == []
    assert "X1 L2 external API failed" in caplog.text


def test_l2_fetch_external_events_http_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """5. При HTTP-ошибке (500) возвращается [] с предупреждением в лог."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error", request=MagicMock(), response=mock_resp
    )

    monkeypatch.setattr(httpx.Client, "get", lambda *_a, **_kw: mock_resp)

    t_start = datetime(2026, 9, 27, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 27, 23, 59, tzinfo=UTC)
    with caplog.at_level("WARNING"):
        res = l2.fetch_external_events(t_start, t_end)

    assert res == []
    assert "X1 L2 external API failed" in caplog.text


def test_cascade_l2_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """6. При доступном L2 порт возвращает внешние события без обращения к L1/L0."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    ev = sample_external_event()
    monkeypatch.setattr(l2, "fetch_external_events", lambda *_a, **_kw: [ev])

    t_start = datetime(2026, 9, 27, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 27, 23, 59, tzinfo=UTC)
    res = events.get_events(t_start, t_end)
    assert len(res) == 1
    assert res[0].id == "e_ext_1"


def test_cascade_l2_empty_or_error_falls_back_to_l1(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """7. При пустом ответе или ошибке L2 происходит откат на L1 (БД)."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    monkeypatch.setattr(l2, "fetch_external_events", lambda *_a, **_kw: [])

    repo = MagicMock()
    ev_db = models.Event(
        id="e_db_1",
        title="Ярмарка ремесел",
        location=models.GeoPoint(lat=47.020, lon=28.830),
        starts_at=datetime(2026, 9, 27, 9, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 27, 18, 0, tzinfo=UTC),
    )
    repo.list_events.return_value = [ev_db]

    t_start = datetime(2026, 9, 27, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 27, 23, 59, tzinfo=UTC)
    with caplog.at_level("WARNING"):
        res = events.get_events(t_start, t_end, repo=repo)

    assert len(res) == 1
    assert res[0].id == "e_db_1"
    repo.list_events.assert_called_once_with(t_start, t_end)
    assert (
        "X1: L2 fetch_external_events returned empty list, falling back to L1"
        in caplog.text
    )


def test_cascade_l2_and_l1_fail_falls_back_to_l0(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """8. При отказе L2 и отказе L1 происходит откат на L0 (демо-фикстуру e1)."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    monkeypatch.setattr(l2, "fetch_external_events", lambda *_a, **_kw: [])

    repo = MagicMock()
    repo.list_events.side_effect = RuntimeError("Database offline")

    t_start = datetime(2026, 9, 26, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 28, 23, 59, tzinfo=UTC)
    with caplog.at_level("WARNING"):
        res = events.get_events(t_start, t_end, repo=repo)

    assert any(e.id == "e1" for e in res)
    assert (
        "X1: L2 fetch_external_events returned empty list, falling back to L1"
        in caplog.text
    )
    assert "X1: L1 get_events failed, falling back to L0" in caplog.text


def test_enrich_context_with_l2_cascade(monkeypatch: pytest.MonkeyPatch) -> None:
    """9. enrich_context при OPTIONAL_BLOCKS=on наполняет контекст событиями из L2."""
    monkeypatch.setattr(settings, "OPTIONAL_BLOCKS", "on")
    monkeypatch.setattr(settings, "USE_MOCK", False)
    ev = sample_external_event()
    monkeypatch.setattr(l2, "fetch_external_events", lambda *_a, **_kw: [ev])

    ctx = models.Context(now=datetime(2026, 9, 27, 6, 0, tzinfo=UTC))
    enriched = events.enrich_context(ctx)
    assert len(enriched.events) == 1
    assert enriched.events[0].id == "e_ext_1"


def test_enrich_context_optional_blocks_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """10. При OPTIONAL_BLOCKS=off enrich_context оставляет ctx.events пустым."""
    monkeypatch.setattr(settings, "OPTIONAL_BLOCKS", "off")
    monkeypatch.setattr(settings, "USE_MOCK", False)

    ctx = models.Context(now=datetime(2026, 9, 27, 6, 0, tzinfo=UTC))
    enriched = events.enrich_context(ctx)
    assert enriched.events == []


def test_routes_l2_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    """11. Роут GET /events возвращает внешние события уровня L2."""
    monkeypatch.setattr(settings, "OPTIONAL_BLOCKS", "on")
    monkeypatch.setattr(settings, "USE_MOCK", False)
    ev = sample_external_event()
    monkeypatch.setattr(l2, "fetch_external_events", lambda *_a, **_kw: [ev])

    app.dependency_overrides[get_current_user] = lambda: make_user("citizen")
    r = client.get(
        f"{settings.API_V1_STR}/events?from=2026-09-27T00:00:00Z&to=2026-09-27T23:59:59Z",
        headers={"Authorization": "Bearer mock"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["id"] == "e_ext_1"
