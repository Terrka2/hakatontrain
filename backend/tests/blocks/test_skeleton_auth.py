"""C0 auth flow on an isolated in-memory database; no PostgreSQL or SMTP."""

import json
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api.deps import get_db
from app.core.config import settings
from app.core.db import init_db
from app.main import app
from app.models import User
from app.utils import generate_password_reset_token


@pytest.fixture
def auth_client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        init_db(session)
        initial_ids = set(session.exec(select(User.id)).all())
        init_db(session)
        assert set(session.exec(select(User.id)).all()) == initial_ids
        users = {user.email: user for user in session.exec(select(User)).all()}
        assert users["supervisor@demo.md"].role == "supervisor"
        for i in (1, 2, 3):
            user = users[f"crew{i}@demo.md"]
            assert (user.role, user.crew_id) == ("crew", f"c{i}")

    def session_override() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = session_override
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_demo_accounts_login_with_fixture_crew_ids(auth_client: TestClient) -> None:
    fixture = Path(__file__).resolve().parents[2] / "app/fixtures/demo_city.json"
    crews = json.loads(fixture.read_text(encoding="utf-8"))["crews"]
    accounts = ["supervisor@demo.md"]
    accounts += [f"crew{crew['id'][1:]}@demo.md" for crew in crews]
    for email in accounts:
        response = auth_client.post(
            "/api/v1/login/access-token",
            data={"username": email, "password": settings.DEMO_PASSWORD},
        )
        assert response.status_code == 200, response.text
        assert response.json()["access_token"]
    assert auth_client.get("/api/v1/users/me").status_code == 401


def test_signup_login_and_password_recovery(auth_client: TestClient) -> None:
    email, password = "citizen-c0@example.com", "c0-test-password"
    response = auth_client.post(
        "/api/v1/users/signup",
        json={
            "email": email,
            "password": password,
            "role": "supervisor",
            "is_superuser": True,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "citizen"
    assert response.json()["is_superuser"] is False
    with patch("app.api.routes.login.send_email") as send:
        assert auth_client.post(f"/api/v1/password-recovery/{email}").status_code == 200
        send.assert_called_once()
        assert send.call_args.kwargs["email_to"] == email
        assert "reset-password?token=" in send.call_args.kwargs["html_content"]
    token = generate_password_reset_token(email=email)
    assert (
        auth_client.post(
            "/api/v1/reset-password/",
            json={"token": token, "new_password": "new-c0-password"},
        ).status_code
        == 200
    )
    assert (
        auth_client.post(
            "/api/v1/login/access-token", data={"username": email, "password": password}
        ).status_code
        == 400
    )
    assert (
        auth_client.post(
            "/api/v1/login/access-token",
            data={"username": email, "password": "new-c0-password"},
        ).status_code
        == 200
    )


def test_docs_health_and_optional_routes(auth_client: TestClient) -> None:
    assert auth_client.get("/docs").status_code == 200
    assert auth_client.get("/api/v1/utils/health-check/").status_code == 200
    assert auth_client.post("/api/v1/trips", json={}).status_code == 404
    assert auth_client.get("/api/v1/events").status_code == 404
