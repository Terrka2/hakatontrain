"""Тесты HTTP API роутов /api/v1/crew: авторизация, роли, 401, 403, 404, 409, 422."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.blocks.fieldwork import l0
from app.core.config import settings
from app.main import app
from app.models import User

API_PREFIX = f"{settings.API_V1_STR}/crew"


@pytest.fixture(autouse=True)
def _reset_state() -> Generator[None]:
    l0.reset_state()
    yield
    app.dependency_overrides.clear()
    l0.reset_state()


def make_user(
    role: str, crew_id: str | None = None, is_superuser: bool = False
) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role}@demo.md",
        role=role,
        crew_id=crew_id,
        is_active=True,
        is_superuser=is_superuser,
        hashed_password="mock_hashed_password",
    )


client = TestClient(app)


def test_me_route_auth_and_roles() -> None:
    """GET /crew/me/route: 401 без токена, 403 с чужой ролью, 200 для бригадира."""
    # 401 без токена
    r = client.get(f"{API_PREFIX}/me/route")
    assert r.status_code == 401

    # 403 для citizen
    app.dependency_overrides[get_current_user] = lambda: make_user("citizen")
    r = client.get(f"{API_PREFIX}/me/route", headers={"Authorization": "Bearer mock"})
    assert r.status_code == 403

    # 200 для crew c1
    app.dependency_overrides[get_current_user] = lambda: make_user("crew", "c1")
    r = client.get(f"{API_PREFIX}/me/route", headers={"Authorization": "Bearer mock"})
    assert r.status_code == 200
    data = r.json()
    assert data["crew_id"] == "c1"
    assert len(data["stops"]) == 2

    # 404 если черновик плана
    assert l0._plan is not None
    l0.set_plan(l0._plan.model_copy(update={"status": "draft"}))
    r = client.get(f"{API_PREFIX}/me/route", headers={"Authorization": "Bearer mock"})
    assert r.status_code == 404

    # 404 если у пользователя нет crew_id
    app.dependency_overrides[get_current_user] = lambda: make_user("crew", None)
    r = client.get(f"{API_PREFIX}/me/route", headers={"Authorization": "Bearer mock"})
    assert r.status_code == 404


def test_post_status_auth_and_transitions() -> None:
    """POST /crew/jobs/{job_id}/status: 401, 403, 400, 422, 409, 200."""
    # 401 без авторизации
    r = client.post(
        f"{API_PREFIX}/jobs/job_c1_1/status",
        json={
            "job_id": "job_c1_1",
            "crew_id": "c1",
            "status": "arrived",
            "at": datetime(2026, 9, 26, 8, 30, tzinfo=UTC).isoformat(),
        },
    )
    assert r.status_code == 401

    # 403 с ролью citizen
    app.dependency_overrides[get_current_user] = lambda: make_user("citizen")
    r = client.post(
        f"{API_PREFIX}/jobs/job_c1_1/status",
        headers={"Authorization": "Bearer mock"},
        json={
            "job_id": "job_c1_1",
            "crew_id": "c1",
            "status": "arrived",
            "at": datetime(2026, 9, 26, 8, 30, tzinfo=UTC).isoformat(),
        },
    )
    assert r.status_code == 403

    # 403 если бригада c1 пытается обновить работу бригады c2
    app.dependency_overrides[get_current_user] = lambda: make_user("crew", "c1")
    r = client.post(
        f"{API_PREFIX}/jobs/job_c2_1/status",
        headers={"Authorization": "Bearer mock"},
        json={
            "job_id": "job_c2_1",
            "crew_id": "c1",
            "status": "arrived",
            "at": datetime(2026, 9, 26, 8, 30, tzinfo=UTC).isoformat(),
        },
    )
    assert r.status_code == 403

    # 400 при несовпадении job_id в URL и теле
    r = client.post(
        f"{API_PREFIX}/jobs/job_c1_1/status",
        headers={"Authorization": "Bearer mock"},
        json={
            "job_id": "job_c1_2",
            "crew_id": "c1",
            "status": "arrived",
            "at": datetime(2026, 9, 26, 8, 30, tzinfo=UTC).isoformat(),
        },
    )
    assert r.status_code == 400

    # 409 при переходе pending -> done напрямую
    r = client.post(
        f"{API_PREFIX}/jobs/job_c1_1/status",
        headers={"Authorization": "Bearer mock"},
        json={
            "job_id": "job_c1_1",
            "crew_id": "c1",
            "status": "done",
            "at": datetime(2026, 9, 26, 8, 30, tzinfo=UTC).isoformat(),
            "photo_url": "https://example.com/p.jpg",
        },
    )
    assert r.status_code == 409

    # 200 при валидном переходе pending -> arrived
    r = client.post(
        f"{API_PREFIX}/jobs/job_c1_1/status",
        headers={"Authorization": "Bearer mock"},
        json={
            "job_id": "job_c1_1",
            "crew_id": "c1",
            "status": "arrived",
            "at": datetime(2026, 9, 26, 8, 30, tzinfo=UTC).isoformat(),
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "arrived"

    # 422 при done без photo_url
    r = client.post(
        f"{API_PREFIX}/jobs/job_c1_1/status",
        headers={"Authorization": "Bearer mock"},
        json={
            "job_id": "job_c1_1",
            "crew_id": "c1",
            "status": "done",
            "at": datetime(2026, 9, 26, 9, 0, tzinfo=UTC).isoformat(),
            "photo_url": None,
        },
    )
    assert r.status_code == 422

    # 200 при done с photo_url
    r = client.post(
        f"{API_PREFIX}/jobs/job_c1_1/status",
        headers={"Authorization": "Bearer mock"},
        json={
            "job_id": "job_c1_1",
            "crew_id": "c1",
            "status": "done",
            "at": datetime(2026, 9, 26, 9, 0, tzinfo=UTC).isoformat(),
            "photo_url": "https://example.com/pothole.jpg",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "done"


def test_progress_route_auth_and_roles() -> None:
    """GET /crew/progress: 401 без токена, 403 для crew, 200 для supervisor, 404 для неизвестного plan_id."""
    # 401 без токена
    r = client.get(f"{API_PREFIX}/progress")
    assert r.status_code == 401

    # 403 для роли crew
    app.dependency_overrides[get_current_user] = lambda: make_user("crew", "c1")
    r = client.get(f"{API_PREFIX}/progress", headers={"Authorization": "Bearer mock"})
    assert r.status_code == 403

    # 200 для supervisor
    app.dependency_overrides[get_current_user] = lambda: make_user("supervisor")
    r = client.get(f"{API_PREFIX}/progress", headers={"Authorization": "Bearer mock"})
    assert r.status_code == 200
    data = r.json()
    assert "c1" in data
    assert data["c1"]["pending"] == 2

    # 404 для неизвестного плана
    r = client.get(
        f"{API_PREFIX}/progress?plan_id=unknown_plan",
        headers={"Authorization": "Bearer mock"},
    )
    assert r.status_code == 404
