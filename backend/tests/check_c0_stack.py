"""Explicit integration check against the isolated C0 Docker stack."""

import html
import re
import time
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx


def test_c0_stack() -> None:
    api = "http://127.0.0.1:18000"
    mailpit = "http://127.0.0.1:18025"
    with httpx.Client(timeout=5) as client:
        for path in ("/", "/docs", "/api/v1/utils/health-check/"):
            assert client.get(api + path).status_code == 200, path

        for email, role, crew_id in [
            ("supervisor@demo.md", "supervisor", None),
            ("crew1@demo.md", "crew", "c1"),
            ("crew2@demo.md", "crew", "c2"),
            ("crew3@demo.md", "crew", "c3"),
        ]:
            login = client.post(
                api + "/api/v1/login/access-token",
                data={
                    "username": email,
                    "password": "demo-citytriage",
                },
            )
            login.raise_for_status()
            me = client.get(
                api + "/api/v1/users/me",
                headers={
                    "Authorization": f"Bearer {login.json()['access_token']}",
                },
            )
            me.raise_for_status()
            assert (me.json()["role"], me.json()["crew_id"]) == (role, crew_id)

        email = f"c0-{uuid4().hex}@example.com"
        password = "c0-integration-password"
        signup = client.post(
            api + "/api/v1/users/signup",
            json={
                "email": email,
                "password": password,
                "role": "supervisor",
            },
        )
        signup.raise_for_status()
        assert signup.json()["role"] == "citizen"
        recovery = client.post(api + f"/api/v1/password-recovery/{email}")
        recovery.raise_for_status()
        messages = []
        for _ in range(20):
            result = client.get(
                mailpit + "/api/v1/search", params={"query": f"to:{email}", "limit": 1}
            )
            result.raise_for_status()
            messages = result.json()["messages"]
            if messages:
                break
            time.sleep(0.1)
        assert messages, "Password recovery email did not arrive in Mailpit"
        message = client.get(mailpit + f"/view/{messages[0]['ID']}.html")
        message.raise_for_status()
        links = re.findall(r'href="([^"]*reset-password\?token=[^"]+)"', message.text)
        assert links, "Email must contain a password reset link"
        reset_url = urlparse(html.unescape(links[0]))
        assert reset_url.netloc == "localhost:18000"
        token = parse_qs(reset_url.query)["token"][0]
        reset = client.post(
            api + "/api/v1/reset-password/",
            json={
                "token": token,
                "new_password": "c0-changed-password",
            },
        )
        reset.raise_for_status()
        for candidate, status in [(password, 400), ("c0-changed-password", 200)]:
            login = client.post(
                api + "/api/v1/login/access-token",
                data={
                    "username": email,
                    "password": candidate,
                },
            )
            assert login.status_code == status
