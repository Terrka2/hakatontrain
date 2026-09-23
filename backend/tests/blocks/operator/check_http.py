"""Explicit live smoke check: python -m tests.blocks.operator.check_http.

Requires the local B0 API on :18001 and seeded demo users. Changes only its
in-memory review/plan state; no mocks or dependency overrides are used.
"""

import json
import logging
from pathlib import Path

import httpx

log = logging.getLogger(__name__)


def main() -> None:
    fixture = json.loads(
        (Path(__file__).resolve().parents[3] / "app/fixtures/demo_city.json").read_text(
            encoding="utf-8"
        )
    )
    with httpx.Client(base_url="http://127.0.0.1:18001", timeout=5) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/api/v1/utils/health-check/").status_code == 200
        assert client.get("/api/v1/clusters").status_code == 401

        def login(email: str) -> dict[str, str]:
            response = client.post(
                "/api/v1/login/access-token",
                data={"username": email, "password": "demo-citytriage"},
            )
            response.raise_for_status()
            return {"Authorization": "Bearer " + response.json()["access_token"]}

        supervisor = login("supervisor@demo.md")
        crew = login("crew1@demo.md")
        assert (
            client.post(
                "/api/v1/operator/run", json={"trigger": "manual"}, headers=crew
            ).status_code
            == 403
        )
        response = client.get("/api/v1/clusters", headers=supervisor)
        response.raise_for_status()
        rows = response.json()
        assert len(rows) == fixture["expect"]["clusters"]
        assert set(fixture["expect"]["top2_priority_reports"]) <= {
            rid for c in rows[:2] for rid in c["report_ids"]
        }
        assert all(c["priority"]["factors"] for c in rows)
        ids = {rid: c["id"] for c in rows for rid in c["report_ids"]}
        assert (
            client.get("/api/v1/clusters/missing", headers=supervisor).status_code
            == 404
        )
        assert (
            client.get("/api/v1/clusters?min_score=-1", headers=supervisor).status_code
            == 422
        )
        assert (
            client.post(
                f"/api/v1/clusters/{ids['r006']}/review",
                json={"decision": "accept"},
                headers=crew,
            ).status_code
            == 403
        )
        for rid in ("r005", "r006"):
            response = client.post(
                f"/api/v1/clusters/{ids[rid]}/review",
                json={"decision": "accept"},
                headers=supervisor,
            )
            response.raise_for_status()
        run = client.post(
            "/api/v1/operator/run", json={"trigger": "manual"}, headers=supervisor
        )
        run.raise_for_status()
        result = run.json()
        assert ids["r006"] not in result["needs_review"]
        plan = client.get("/api/v1/plan/" + result["plan_id"], headers=supervisor)
        plan.raise_for_status()
        draft = plan.json()
        assert draft["status"] == "draft" and draft["approved_by"] is None
        assert any(
            ids["r006"] in stop["job_id"]
            for route in draft["routes"]
            for stop in route["stops"]
        )
        assert (
            client.get("/api/v1/operator/runs?limit=1", headers=supervisor).json()[0][
                "id"
            ]
            == result["id"]
        )
        log.info(
            "B0 live HTTP passed: %s clusters, %s routes, supervisor/crew access checked",
            len(rows),
            len(draft["routes"]),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    main()
