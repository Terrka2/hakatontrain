"""Тесты HTTP API роутов B6 (/api/v1/plan, /api/v1/crews): авторизация, роли, 401/403/404/422."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.blocks import dispatch
from app.blocks.dispatch import store
from app.contracts.models import Context
from app.core.config import settings
from app.main import app
from app.models import User

API = settings.API_V1_STR


@pytest.fixture(autouse=True)
def _reset_store() -> Generator[None]:
    store.reset()
    yield
    app.dependency_overrides.clear()
    store.reset()


def make_user(role: str, is_superuser: bool = False) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role}@demo.md",
        role=role,
        is_active=True,
        is_superuser=is_superuser,
        hashed_password="mock_hashed_password",
    )


client = TestClient(app)


def _seed_plan(day: int = 26) -> None:
    """Кладёт в хранилище B6 детерминированный план (минуя HTTP POST /plan).

    `day` меняет ctx.now.date() (=> Plan.day), чтобы получить план с другим
    (детерминированным) id — solve() хэширует содержимое плана, а с пустым списком
    задач маршруты не зависят от времени внутри суток, только от даты.
    """
    crews = dispatch.get_crews()
    ctx = Context(now=datetime(2026, 9, day, 8, tzinfo=UTC))
    plan = dispatch.solve([], crews, ctx)
    dispatch.record_plan(plan)


def test_crews_route_auth() -> None:
    """GET /crews: 401 без токена, 200 со списком бригад из fixture для любой роли."""
    r = client.get(f"{API}/crews")
    assert r.status_code == 401

    app.dependency_overrides[get_current_user] = lambda: make_user("citizen")
    r = client.get(f"{API}/crews", headers={"Authorization": "Bearer mock"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == len(dispatch.get_crews())
    assert {c["id"] for c in body} == {c.id for c in dispatch.get_crews()}


def test_create_plan_success_via_real_pipeline() -> None:
    """POST /plan: реальный конвейер B1->B3->B4->B5->B6 отдаёт валидный черновик плана."""
    app.dependency_overrides[get_current_user] = lambda: make_user("supervisor")
    r = client.post(
        f"{API}/plan",
        headers={"Authorization": "Bearer mock"},
        json={"day": "2026-09-26"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "draft"
    assert body["day"] == "2026-09-26"
    assert body["routes"]


def test_create_plan_reports_503_when_dependency_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /plan: ошибка неготового соседнего блока (NotImplementedError) -> 503, не 500."""
    from app.blocks import clusters

    def _not_ready(*args: object, **kwargs: object) -> None:
        raise NotImplementedError("B3: временно недоступен")

    monkeypatch.setattr(clusters, "build_clusters", _not_ready)
    app.dependency_overrides[get_current_user] = lambda: make_user("supervisor")
    r = client.post(
        f"{API}/plan",
        headers={"Authorization": "Bearer mock"},
        json={"day": "2026-09-26"},
    )
    assert r.status_code == 503


def test_create_plan_requires_auth_and_validates_body() -> None:
    """POST /plan: 401 без токена, 422 при кривом теле."""
    r = client.post(f"{API}/plan", json={"day": "2026-09-26"})
    assert r.status_code == 401

    app.dependency_overrides[get_current_user] = lambda: make_user("supervisor")
    r = client.post(
        f"{API}/plan",
        headers={"Authorization": "Bearer mock"},
        json={"day": "not-a-date"},
    )
    assert r.status_code == 422


def test_current_and_draft_and_by_id_routes() -> None:
    """GET /plan/current, /plan/draft, /plan/{id}: 401, 404 без плана, 200 после seed."""
    r = client.get(f"{API}/plan/current")
    assert r.status_code == 401

    app.dependency_overrides[get_current_user] = lambda: make_user("supervisor")
    r = client.get(f"{API}/plan/current", headers={"Authorization": "Bearer mock"})
    assert r.status_code == 404
    r = client.get(f"{API}/plan/draft", headers={"Authorization": "Bearer mock"})
    assert r.status_code == 404
    r = client.get(f"{API}/plan/unknown_id", headers={"Authorization": "Bearer mock"})
    assert r.status_code == 404

    _seed_plan()
    r = client.get(f"{API}/plan/draft", headers={"Authorization": "Bearer mock"})
    assert r.status_code == 200
    plan_id = r.json()["id"]
    assert r.json()["status"] == "draft"

    r = client.get(f"{API}/plan/{plan_id}", headers={"Authorization": "Bearer mock"})
    assert r.status_code == 200
    assert r.json()["id"] == plan_id

    # ещё не approved -> /current остаётся 404
    r = client.get(f"{API}/plan/current", headers={"Authorization": "Bearer mock"})
    assert r.status_code == 404


def test_approve_roles_and_supersede() -> None:
    """Критерий 5: approve от crew -> 403; от supervisor -> approved, предыдущий -> superseded."""
    _seed_plan()
    app.dependency_overrides[get_current_user] = lambda: make_user("supervisor")
    first_id = client.get(
        f"{API}/plan/draft", headers={"Authorization": "Bearer mock"}
    ).json()["id"]

    del app.dependency_overrides[get_current_user]  # проверяем 401 без переопределения
    r = client.post(f"{API}/plan/{first_id}/approve")
    assert r.status_code == 401

    app.dependency_overrides[get_current_user] = lambda: make_user("crew")
    r = client.post(
        f"{API}/plan/{first_id}/approve", headers={"Authorization": "Bearer mock"}
    )
    assert r.status_code == 403

    app.dependency_overrides[get_current_user] = lambda: make_user("supervisor")
    r = client.post(
        f"{API}/plan/{first_id}/approve", headers={"Authorization": "Bearer mock"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
    assert r.json()["approved_by"] == "supervisor@demo.md"

    r = client.post(
        f"{API}/plan/unknown_id/approve", headers={"Authorization": "Bearer mock"}
    )
    assert r.status_code == 404

    # второй план вытесняет первый (superseded)
    _seed_plan(day=27)
    second_id = client.get(
        f"{API}/plan/draft", headers={"Authorization": "Bearer mock"}
    ).json()["id"]
    assert second_id != first_id
    r = client.post(
        f"{API}/plan/{second_id}/approve", headers={"Authorization": "Bearer mock"}
    )
    assert r.status_code == 200

    r = client.get(f"{API}/plan/{first_id}", headers={"Authorization": "Bearer mock"})
    assert r.json()["status"] == "superseded"
    r = client.get(f"{API}/plan/current", headers={"Authorization": "Bearer mock"})
    assert r.json()["id"] == second_id


def test_superuser_bypasses_role_check() -> None:
    """Суперпользователь проходит require_roles независимо от role."""
    _seed_plan()
    app.dependency_overrides[get_current_user] = lambda: make_user(
        "citizen", is_superuser=True
    )
    plan_id = client.get(
        f"{API}/plan/draft", headers={"Authorization": "Bearer mock"}
    ).json()["id"]
    r = client.post(
        f"{API}/plan/{plan_id}/approve", headers={"Authorization": "Bearer mock"}
    )
    assert r.status_code == 200
