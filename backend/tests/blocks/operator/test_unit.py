"""Tests B0 orchestration with explicit neighbour doubles; no external services."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.blocks import clusters, extractor, operator
from app.contracts.models import JobUpdate
from app.models import User


def test_pipeline_and_step_order(neighbours: SimpleNamespace) -> None:
    n = neighbours
    run = operator.operator_run("manual", n.now)
    assert run.clusters_total == n.data["expect"]["clusters"]
    assert run.clusters_new == run.clusters_total
    assert run.needs_review == ["r006"]
    assert run.plan_id
    plan = operator.get_plan(run.plan_id)
    assert plan.status == "draft" and plan.approved_by is None
    stages = list(dict.fromkeys(n.events))
    assert stages == [
        "load_fixture",
        "extract",
        "verify",
        "build_clusters",
        "build_context",
        "score",
        "make_jobs",
        "solve",
    ]
    assert n.events.count("extract") == len(n.reports)
    assert n.events.count("verify") == len(n.reports)
    assert "13 проблем" in run.summary


def test_repeatability_and_snapshot_isolation(neighbours: SimpleNamespace) -> None:
    n = neighbours
    before = [r.model_dump() for r in n.reports]
    assert operator.run_pipeline(n.reports, n.now) == operator.run_pipeline(
        n.reports, n.now
    )
    assert before == [r.model_dump() for r in n.reports]
    first = operator.operator_run("manual", n.now)
    second = operator.operator_run("manual", n.now)
    assert second.clusters_new == 0
    assert (
        operator.get_plan(first.plan_id).routes
        == operator.get_plan(second.plan_id).routes
    )
    assert operator.get_runs(1)[0].id == second.id
    operator.get_runs()[0].summary = "tampered"
    operator.get_cluster("r006").priority.needs_review = False
    assert operator.get_runs()[0].summary != "tampered"
    assert operator.get_cluster("r006").priority.needs_review


@pytest.mark.parametrize("stage", ["score", "make_jobs", "solve"])
def test_neighbour_failures_keep_clusters(
    neighbours: SimpleNamespace, stage: str, caplog: pytest.LogCaptureFixture
) -> None:
    getattr(neighbours, stage).side_effect = RuntimeError("private diagnostic")
    run = operator.operator_run("manual", neighbours.now)
    assert run.plan_id is None
    assert len(operator.get_clusters()) == neighbours.data["expect"]["clusters"]
    assert any("Ошибка" in d.reason for d in run.decisions)
    assert "failed" in caplog.text
    assert "private diagnostic" not in run.model_dump_json()
    if stage == "score":
        neighbours.make_jobs.assert_not_called()
        assert all(c.priority is None for c in operator.get_clusters())


def test_api_filters_detail_review_and_runs(
    neighbours: SimpleNamespace, api: TestClient
) -> None:
    response = api.get("/api/v1/clusters?sort=priority")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == neighbours.data["expect"]["clusters"]
    assert {c["id"] for c in rows[:2]} == {"r001", "r011"}
    assert all(c["priority"]["factors"] for c in rows)
    assert len(api.get("/api/v1/clusters?min_score=80").json()) == 2
    assert all(
        c["category"] == "pothole"
        for c in api.get("/api/v1/clusters?category=pothole").json()
    )
    detail = api.get("/api/v1/clusters/r001").json()
    assert {r["id"] for r in detail["reports"]} == set(
        neighbours.data["expect"]["dup_trio"]
    )
    assert (
        api.post("/api/v1/clusters/r006/review", json={"decision": "accept"}).json()[
            "priority"
        ]["needs_review"]
        is False
    )
    response = api.post("/api/v1/operator/run", json={"trigger": "manual"})
    assert response.status_code == 200
    run = response.json()
    assert "r006" not in run["needs_review"]
    assert any(
        s.job_id == "r006"
        for r in operator.get_plan(run["plan_id"]).routes
        for s in r.stops
    )
    assert api.get("/api/v1/operator/runs?limit=1").json()[0]["id"] == run["id"]


def test_reject_excludes_cluster(neighbours: SimpleNamespace) -> None:
    operator.operator_run("manual", neighbours.now)
    operator.review_cluster("r006", "reject")
    run = operator.operator_run("manual", neighbours.now)
    assert "r006" not in run.needs_review
    assert "r006" not in {c.id for c in neighbours.make_jobs.call_args.args[0]}


@pytest.mark.parametrize(
    "path,body",
    [
        ("/clusters/r006/review", {"decision": "accept"}),
        ("/operator/run", {"trigger": "manual"}),
    ],
)
def test_write_requires_supervisor(
    neighbours: SimpleNamespace, api: TestClient, path: str, body: dict[str, str]
) -> None:
    api.app.dependency_overrides[get_current_user] = lambda: User(
        email="crew1@demo.md", role="crew", hashed_password="unused"
    )
    assert api.post("/api/v1" + path, json=body).status_code == 403
    assert neighbours.events == []


def test_validation_not_found_and_unauthenticated(
    neighbours: SimpleNamespace, api: TestClient
) -> None:
    assert neighbours.events == []
    assert api.get("/api/v1/clusters/missing").status_code == 404
    assert (
        api.post(
            "/api/v1/clusters/missing/review", json={"decision": "accept"}
        ).status_code
        == 404
    )
    for url in (
        "/clusters?min_score=-1",
        "/clusters?sort=bad",
        "/operator/runs?limit=0",
    ):
        assert api.get("/api/v1" + url).status_code == 422
    assert (
        api.post("/api/v1/clusters/r006/review", json={"decision": "bad"}).status_code
        == 422
    )
    assert (
        api.post("/api/v1/operator/run", json={"trigger": "job_update"}).status_code
        == 422
    )
    api.app.dependency_overrides.clear()
    assert api.get("/api/v1/clusters").status_code == 401
    assert api.get("/api/v1/operator/runs").status_code == 401


def test_missing_dependencies_return_503(
    neighbours: SimpleNamespace, api: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert neighbours.events == []
    monkeypatch.setattr(
        extractor, "extract", Mock(side_effect=NotImplementedError("unavailable"))
    )
    assert api.get("/api/v1/clusters").status_code == 503
    assert (
        api.post("/api/v1/operator/run", json={"trigger": "manual"}).status_code == 503
    )
    assert operator.get_runs() == []


def test_job_update_calls_only_replan(neighbours: SimpleNamespace) -> None:
    n = neighbours
    operator.operator_run("manual", n.now)
    n.solve.reset_mock()
    update = JobUpdate(
        job_id="r001",
        crew_id=n.crews[0].id,
        status="failed",
        reason="no_access",
        at=n.now,
    )
    run = operator.operator_run("job_update", n.now, update)
    n.replan.assert_called_once()
    n.solve.assert_not_called()
    assert operator.get_plan(run.plan_id).status == "draft"


def test_empty_and_invalid_inputs(
    neighbours: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(clusters, "build_clusters", Mock(return_value=[]))
    empty = operator.run_pipeline([], neighbours.now)
    assert empty.clusters == [] and empty.priorities == {}
    neighbours.score.assert_not_called()
    with pytest.raises(ValueError):
        operator.run_pipeline([neighbours.reports[0]] * 2, neighbours.now)
    with pytest.raises(ValueError):
        operator.run_pipeline([], neighbours.now.replace(tzinfo=None))
    with pytest.raises(ValueError):
        operator.operator_run("bad", neighbours.now)
    with pytest.raises(ValueError):
        operator.operator_run("job_update", neighbours.now)


def test_runs_sorted_by_time(neighbours: SimpleNamespace) -> None:
    newer = operator.operator_run("manual", neighbours.now + timedelta(days=1))
    operator.operator_run("manual", neighbours.now)
    assert operator.get_runs(1)[0].id == newer.id
