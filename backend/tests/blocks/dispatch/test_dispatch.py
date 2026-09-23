import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from app.blocks import context
from app.blocks.dispatch import make_jobs, replan, solve
from app.blocks.operator import run_pipeline
from app.contracts.models import Crew, JobUpdate, Report


@pytest.fixture
def inputs() -> tuple[Any, list[Crew], list[Any], list[Any]]:
    data = json.loads(
        (Path(__file__).resolve().parents[3] / "app/fixtures/demo_city.json").read_text(
            encoding="utf-8"
        )
    )
    context.reset_scenario()
    result = run_pipeline(
        [Report.model_validate(r) for r in data["reports"]],
        datetime.fromisoformat(data["now"]),
    )
    jobs, decisions = make_jobs(result.clusters, result.priorities, result.context)
    return result, [Crew.model_validate(c) for c in data["crews"]], jobs, decisions


def test_batching_and_route_constraints(
    inputs: tuple[Any, list[Crew], list[Any], list[Any]],
) -> None:
    result, crews, jobs, decisions = inputs
    assert len(jobs) == 9
    batch = next(j for j in jobs if "cl_r007" in j.cluster_ids)
    assert set(batch.cluster_ids) == {f"cl_r00{i}" for i in (7, 8, 9)} | {"cl_r010"}
    assert batch.service_min == 144
    assert all("cl_r006" not in j.cluster_ids for j in jobs)
    assert any(d.subject_id == "cl_r006" for d in decisions)
    plan = solve(jobs, crews, result.context)
    assert plan == solve(jobs, crews, result.context)
    assert plan.total_priority >= plan.baseline_total_priority
    by_id = {j.id: j for j in jobs}
    for route in plan.routes:
        crew = next(c for c in crews if c.id == route.crew_id)
        for stop in route.stops:
            assert by_id[stop.job_id].skill in crew.skills
            assert crew.shift_start <= stop.arrival <= stop.departure <= crew.shift_end


def test_deadline_and_short_shifts(
    inputs: tuple[Any, list[Crew], list[Any], list[Any]],
) -> None:
    result, crews, jobs, _ = inputs
    deadline_job = jobs[0].model_copy(update={"deadline": result.context.now})
    plan = solve([deadline_job], crews, result.context)
    assert deadline_job.id in plan.unassigned
    assert any(d.subject_id == deadline_job.id for d in plan.decisions)
    short = [
        c.model_copy(update={"shift_end": c.shift_start + timedelta(hours=2)})
        for c in crews
    ]
    plan = solve(jobs, short, result.context)
    assert plan.unassigned
    assert set(plan.unassigned) <= {d.subject_id for d in plan.decisions}


def test_replan_preserves_done_and_changes_skill(
    inputs: tuple[Any, list[Crew], list[Any], list[Any]],
) -> None:
    result, crews, jobs, _ = inputs
    plan = solve(jobs, crews, result.context)
    route = next(r for r in plan.routes if r.crew_id == "c1")
    assert len(route.stops) >= 2
    route.stops[0].status = "done"
    stable = route.stops[0].model_copy(deep=True)
    failed = route.stops[1]
    update = JobUpdate(
        job_id=failed.job_id,
        crew_id="c1",
        status="failed",
        at=stable.departure,
        reason="needs_other_skill",
        needs_skill="electric",
    )
    updated = replan(plan, update, jobs, crews, result.context)
    assert updated.version == plan.version + 1 and updated.status == "draft"
    assert next(r for r in updated.routes if r.crew_id == "c1").stops[0] == stable
    assert any(
        s.job_id == failed.job_id
        for r in updated.routes
        if r.crew_id == "c2"
        for s in r.stops
    )
    not_found = replan(
        plan,
        update.model_copy(update={"reason": "not_found"}),
        jobs,
        crews,
        result.context,
    )
    assert any(d.kind == "review" for d in not_found.decisions)
    assert all(s.job_id != failed.job_id for r in not_found.routes for s in r.stops)


def test_storm_applies_real_context_rules(
    inputs: tuple[Any, list[Crew], list[Any], list[Any]],
) -> None:
    result, crews, _, _ = inputs
    context.set_scenario("storm")
    try:
        storm = context.build_context(result.context.now)
        jobs, decisions = make_jobs(result.clusters, result.priorities, storm)
        potholes = {c.id for c in result.clusters if c.category == "pothole"}
        assert all(not potholes.intersection(j.cluster_ids) for j in jobs)
        assert any(d.kind == "defer" for d in decisions)
        tree = next(j for j in jobs if j.skill == "green")
        assert any(
            s.job_id == tree.id
            for r in solve(jobs, crews, storm).routes
            for s in r.stops
        )
    finally:
        context.reset_scenario()
