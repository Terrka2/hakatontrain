"""Тесты роутов блока B5 (context): /api/v1/context."""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.config import settings
from app.main import app
from app.models import User


@pytest.fixture(autouse=True)
def _cleanup_overrides() -> Generator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def supervisor_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="supervisor@example.com",
        role="supervisor",
        is_active=True,
        is_superuser=False,
        hashed_password="fake",
    )


@pytest.fixture
def citizen_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="citizen@example.com",
        role="citizen",
        is_active=True,
        is_superuser=False,
        hashed_password="fake",
    )


def test_get_context_unauthorized(client: TestClient) -> None:
    """Запрос без токена -> 401 Unauthorized."""
    response = client.get(f"{settings.API_V1_STR}/context")
    assert response.status_code == 401


def test_get_context_success(client: TestClient, citizen_user: User) -> None:
    """Запрос авторизованного пользователя -> 200 и модель Context."""
    app.dependency_overrides[get_current_user] = lambda: citizen_user
    response = client.get(f"{settings.API_V1_STR}/context")
    assert response.status_code == 200
    data = response.json()
    assert "now" in data
    assert "weather" in data
    assert "infrastructure" in data
    assert len(data["infrastructure"]) == 3
    assert data["events"] == []


def test_put_weather_scenario_unauthorized(client: TestClient) -> None:
    """Смена сценария без токена -> 401."""
    response = client.put(
        f"{settings.API_V1_STR}/context/weather-scenario",
        json={"scenario": "storm"},
    )
    assert response.status_code == 401


def test_put_weather_scenario_forbidden_for_non_supervisor(
    client: TestClient, citizen_user: User
) -> None:
    """Смена сценария пользователем с ролью citizen (не supervisor) -> 403 Forbidden."""
    app.dependency_overrides[get_current_user] = lambda: citizen_user
    response = client.put(
        f"{settings.API_V1_STR}/context/weather-scenario",
        json={"scenario": "storm"},
    )
    assert response.status_code == 403


def test_put_weather_scenario_success_for_supervisor(
    client: TestClient, supervisor_user: User
) -> None:
    """Смена сценария супервайзером -> 200 и изменение погоды в GET."""
    app.dependency_overrides[get_current_user] = lambda: supervisor_user

    # Устанавливаем сценарий storm
    resp_put = client.put(
        f"{settings.API_V1_STR}/context/weather-scenario",
        json={"scenario": "storm"},
    )
    assert resp_put.status_code == 200
    assert resp_put.json() == {"status": "ok", "scenario": "storm"}

    # Проверяем, что контекст возвращает storm погоду
    resp_get = client.get(f"{settings.API_V1_STR}/context")
    assert resp_get.status_code == 200
    weather = resp_get.json()["weather"]
    assert weather is not None
    assert weather["precipitation_mm"] >= 5.0


def test_put_weather_scenario_validation_error(
    client: TestClient, supervisor_user: User
) -> None:
    """Некорректное тело запроса -> 422 Unprocessable Entity."""
    app.dependency_overrides[get_current_user] = lambda: supervisor_user
    response = client.put(
        f"{settings.API_V1_STR}/context/weather-scenario",
        json={"wrong_field": 123},
    )
    assert response.status_code == 422


def test_context_nonexistent_endpoint(
    client: TestClient, supervisor_user: User
) -> None:
    """Несуществующий эндпоинт -> 404."""
    app.dependency_overrides[get_current_user] = lambda: supervisor_user
    response = client.get(f"{settings.API_V1_STR}/context/nonexistent")
    assert response.status_code == 404
