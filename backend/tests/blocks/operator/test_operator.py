"""B0 acceptance checks against real ports; missing dependencies stay visible."""

import json
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.blocks import dispatch, operator, priority
from app.blocks.operator import dto, operator_run, run_pipeline
from app.contracts.models import Report


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("B0 L0 must not connect to the network")

    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture
def data() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / "app/fixtures/demo_city.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def reports(data: dict[str, Any]) -> list[Report]:
    return [Report.model_validate(row) for row in data["reports"]]


@pytest.fixture
def now(data: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(data["weather"]["clear"]["at"])


def test_cluster_response_model_is_available() -> None:
    # ClusterOut/ClusterDetail are B0's own response DTOs (contracts/models.py is frozen —
    # AGENTS.md п.2 — and does not define B0-specific API response shapes).
    assert hasattr(dto, "ClusterOut"), "B0 contract requires a canonical ClusterOut DTO"


def test_pipeline_clusters_and_top_priorities(
    data: dict[str, Any], reports: list[Report], now: datetime
) -> None:
    result = run_pipeline(reports, now)
    assert len(result.clusters) == data["expect"]["clusters"]
    ranked = sorted(
        result.clusters,
        key=lambda cluster: (-result.priorities[cluster.id].score, cluster.id),
    )
    top_reports = {
        report_id for cluster in ranked[:2] for report_id in cluster.report_ids
    }
    assert set(data["expect"]["top2_priority_reports"]) <= top_reports


def test_pipeline_factors_and_review(
    data: dict[str, Any], reports: list[Report], now: datetime
) -> None:
    result = run_pipeline(reports, now)
    assert result.clusters
    for cluster in result.clusters:
        priority = result.priorities[cluster.id]
        assert priority.factors
        if data["expect"]["suspicious_report"] in cluster.report_ids:
            assert priority.needs_review
    assert any(
        data["expect"]["suspicious_report"] in cluster.report_ids
        for cluster in result.clusters
    )


def test_manual_run_links_plan_and_review(
    data: dict[str, Any], reports: list[Report], now: datetime
) -> None:
    pipeline = run_pipeline(reports, now)
    suspicious = next(
        cluster.id
        for cluster in pipeline.clusters
        if data["expect"]["suspicious_report"] in cluster.report_ids
    )
    result = operator_run("manual", now)
    assert result.clusters_total == data["expect"]["clusters"]
    assert suspicious in result.needs_review
    assert result.plan_id is not None


def test_pipeline_is_deterministic(reports: list[Report], now: datetime) -> None:
    original = [report.model_dump(mode="json") for report in reports]
    assert run_pipeline(reports, now) == run_pipeline(reports, now)
    assert [report.model_dump(mode="json") for report in reports] == original


def test_real_api_review_to_plan(api: TestClient, data: dict[str, Any]) -> None:
    """Only authentication is isolated; all business ports run their actual L0."""
    rows = api.get("/api/v1/clusters").json()
    assert len(rows) == data["expect"]["clusters"]
    assert {r for c in rows[:2] for r in c["report_ids"]} >= set(
        data["expect"]["top2_priority_reports"]
    )
    ids = {rid: c["id"] for c in rows for rid in c["report_ids"]}
    before = api.get("/api/v1/plan/draft").json()
    assert before["status"] == "draft"
    assert api.get("/api/v1/plan/" + before["id"]).status_code == 200
    assert not any(
        ids["r006"] in s["job_id"] for r in before["routes"] for s in r["stops"]
    )
    assert (
        api.post(
            f"/api/v1/clusters/{ids['r006']}/review", json={"decision": "accept"}
        ).status_code
        == 200
    )
    run = api.post("/api/v1/operator/run", json={"trigger": "manual"}).json()
    after = api.get("/api/v1/plan/" + run["plan_id"]).json()
    assert after["status"] == "draft" and after["approved_by"] is None
    assert any(ids["r006"] in s["job_id"] for r in after["routes"] for s in r["stops"])
    assert ids["r006"] not in run["needs_review"]
    assert api.get("/api/v1/operator/runs?limit=1").json()[0]["id"] == run["id"]


def test_real_repeated_routes_and_review_reason(now: datetime) -> None:
    first = operator_run("manual", now)
    second = operator_run("manual", now)
    assert (
        operator.get_plan(first.plan_id).routes
        == operator.get_plan(second.plan_id).routes
    )
    assert second.clusters_new == 0
    # A second review is a genuine extractor result, not a scheduler count fix.
    extra = operator.get_cluster("cl_r005")
    assert extra.priority.needs_review
    assert len(extra.reports[0].verification.reasons) >= 3
    operator.review_cluster(extra.id, "accept")
    accepted = operator_run("manual", now)
    assert extra.id not in accepted.needs_review
    assert any(
        extra.id in s.job_id
        for r in operator.get_plan(accepted.plan_id).routes
        for s in r.stops
    )


@pytest.mark.parametrize("stage", ["score", "make_jobs", "solve"])
def test_real_dependency_failure(
    now: datetime, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    def broken(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("B0 injected dependency failure")

    monkeypatch.setattr(priority if stage == "score" else dispatch, stage, broken)
    run = operator_run("manual", now)
    assert run.plan_id is None and run.clusters_total == 13
    assert run.decisions and len(operator.get_clusters()) == 13


def test_real_empty_single_optional_and_timezones(
    reports: list[Report], now: datetime
) -> None:
    empty = run_pipeline([], now)
    assert empty.clusters == [] and empty.priorities == {}
    single = reports[0].model_copy(
        deep=True, update={"address": None, "photo_url": None, "lang": None}
    )
    result = run_pipeline([single], now)
    assert len(result.clusters) == 1
    uppercase = single.model_copy(update={"text": "  " + single.text.upper() + "  "})
    assert run_pipeline([uppercase], now) == result
    utc_rows = [
        r.model_copy(update={"created_at": r.created_at.astimezone(UTC)})
        for r in reports
    ]
    assert run_pipeline(utc_rows, now.astimezone(UTC)) == run_pipeline(reports, now)
    midnight = now.replace(hour=23, minute=59) + timedelta(minutes=1)
    assert len(run_pipeline(reports, midnight).clusters) == 13
