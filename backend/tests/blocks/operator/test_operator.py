"""B0 acceptance checks against real ports; missing dependencies stay visible."""

import json
import socket
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from app.blocks.operator import operator_run, run_pipeline
from app.contracts import models
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
    assert hasattr(models, "ClusterOut"), "B0 contract requires canonical ClusterOut"


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
