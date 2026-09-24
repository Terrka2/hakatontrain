"""Fixture-derived doubles for B0 unit tests, not acceptance of neighbour blocks."""

import json
import socket
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes import clusters as clusters_api
from app.api.routes import operator as operator_api
from app.api.routes import plan as plan_api
from app.blocks import clusters, context, dispatch, extractor, ingest, priority
from app.blocks.dispatch import store as dispatch_store
from app.blocks.operator import l0
from app.contracts.models import (
    CATEGORY_TO_SKILL,
    Cluster,
    Context,
    Crew,
    CrewRoute,
    Extracted,
    Factor,
    Job,
    Plan,
    Priority,
    Report,
    RouteStop,
    Verification,
)
from app.models import User


@pytest.fixture(autouse=True)
def isolated_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("_clusters", "_reviews"):
        monkeypatch.setattr(l0, name, {})
    monkeypatch.setattr(l0, "_runs", [])
    # B0 does not own Plan storage: B6's store.py does (docs/status/B6.md). Reset it too
    # so operator tests stay isolated from each other without duplicating B6's state here.
    dispatch_store.reset()

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("B0 test opened a network connection")

    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture
def fixture_data() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / "app/fixtures/demo_city.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def neighbours(
    monkeypatch: pytest.MonkeyPatch, fixture_data: dict[str, Any]
) -> SimpleNamespace:
    data = fixture_data
    reports = [Report.model_validate(r) for r in data["reports"]]
    now = datetime.fromisoformat(data["now"])
    by_id = {r.id: r for r in reports}
    trio = data["expect"]["dup_trio"]
    groups = [trio] + [
        [r.id] for r in reports if r.id not in trio and r.status == "open"
    ]
    grouped = [
        Cluster(
            id=ids[0],
            category=by_id[ids[0]].category,
            centroid=by_id[ids[0]].location,
            report_ids=ids,
            first_reported_at=min(by_id[i].created_at for i in ids),
            last_reported_at=max(by_id[i].created_at for i in ids),
        )
        for ids in groups
    ]
    scores = {
        c.id: Priority(
            cluster_id=c.id,
            score=90 if c.id == "r011" else 80 if c.id == "r001" else 20,
            factors=[
                Factor(
                    code="HZ", label="test port response", score=1, weight=1, points=20
                )
            ],
            confidence=1,
            needs_review=data["expect"]["suspicious_report"] in c.report_ids,
        )
        for c in grouped
    }
    crews = [Crew.model_validate(c) for c in data["crews"]]
    events: list[str] = []

    def stub(module: Any, name: str, action: Any) -> Mock:
        def invoke(*args: Any, **kwargs: Any) -> Any:
            events.append(name)
            return action(*args, **kwargs)

        mocked = Mock(side_effect=invoke)
        monkeypatch.setattr(module, name, mocked)
        return mocked

    stub(ingest, "load_fixture", lambda: [r.model_copy(deep=True) for r in reports])
    stub(extractor, "extract", lambda r: Extracted())
    stub(
        extractor,
        "verify",
        lambda r, nearby: Verification(
            status="suspicious"
            if r.id == data["expect"]["suspicious_report"]
            else "plausible",
            confidence=1,
        ),
    )
    stub(
        clusters,
        "build_clusters",
        lambda rows: [c.model_copy(deep=True) for c in grouped],
    )
    stub(context, "build_context", lambda at: Context(now=at))
    score = stub(
        priority,
        "score",
        lambda c, rows, history, ctx: scores[c.id].model_copy(deep=True),
    )

    def jobs(
        rows: list[Cluster], values: dict[str, Priority], _ctx: Context
    ) -> tuple[list[Job], list[Any]]:
        return [
            Job(
                id=c.id,
                cluster_ids=[c.id],
                location=c.centroid,
                skill=CATEGORY_TO_SKILL[c.category],
                service_min=1,
                priority=int(values[c.id].score),
            )
            for c in rows
            if not values[c.id].needs_review
        ], []

    make_jobs = stub(dispatch, "make_jobs", jobs)

    def plan(jobs: list[Job], team: list[Crew], ctx: Context) -> Plan:
        return Plan(
            id="port-plan",
            day=ctx.now.date(),
            status="approved",
            approved_by="port-must-not-approve",
            routes=[
                CrewRoute(
                    crew_id=team[0].id,
                    stops=[
                        RouteStop(
                            job_id=j.id,
                            location=j.location,
                            arrival=ctx.now,
                            departure=ctx.now,
                        )
                        for j in jobs
                    ],
                )
            ],
        )

    solve = stub(dispatch, "solve", plan)
    replan = stub(
        dispatch, "replan", lambda old, update, jobs, team, ctx: plan(jobs, team, ctx)
    )
    return SimpleNamespace(
        data=data,
        reports=reports,
        now=now,
        clusters=grouped,
        scores=scores,
        crews=crews,
        events=events,
        score=score,
        make_jobs=make_jobs,
        solve=solve,
        replan=replan,
    )


@pytest.fixture
def api() -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(clusters_api.router, prefix="/api/v1")
    app.include_router(operator_api.router, prefix="/api/v1")
    app.include_router(plan_api.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: User(
        email="supervisor@demo.md", role="supervisor", hashed_password="unused"
    )
    with TestClient(app) as client:
        yield client
