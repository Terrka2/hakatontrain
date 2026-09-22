from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import User


def _login(client: TestClient, email: str) -> dict[str, str]:
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": settings.DEMO_PASSWORD},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_demo_users_are_seeded_with_roles(db: Session) -> None:
    users = {u.email: u for u in db.exec(select(User)).all()}
    assert users["supervisor@demo.md"].role == "supervisor"
    assert {users[f"crew{i}@demo.md"].crew_id for i in (1, 2, 3)} == {"c1", "c2", "c3"}


def test_role_is_visible_to_frontend(client: TestClient) -> None:
    me = client.get(
        f"{settings.API_V1_STR}/users/me", headers=_login(client, "crew1@demo.md")
    ).json()
    assert me["role"] == "crew"
    assert me["crew_id"] == "c1"


def test_signup_cannot_grant_itself_a_role(client: TestClient) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json={
            "email": "sneaky@example.com",
            "password": "password1234",
            "role": "supervisor",
        },
    )
    assert r.status_code == 200
    assert r.json()["role"] == "citizen"
