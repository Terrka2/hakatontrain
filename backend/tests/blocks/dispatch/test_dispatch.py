"""Тесты порта блока B6 (make_jobs/solve/replan/baseline_total_priority). Критерии приёмки — по одному.

Данные — реальные соседние блоки: клиенты B3 (`clusters.build_clusters`) и B4 (`priority.score`)
уже приняты в `pair/backend`, контекст — B5. Fixture — только `demo_city.json`, `expect` не меняем.

Запуск: cd backend && uv run pytest tests/blocks/dispatch -q
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NamedTuple

import pytest

from app.blocks import clusters, context, priority
from app.blocks.dispatch import (
    baseline_total_priority,
    make_jobs,
    replan,
    solve,
)
from app.contracts.models import (
    Cluster,
    Context,
    Crew,
    JobUpdate,
    Priority,
    Report,
)

FIXTURE = Path(__file__).resolve().parents[3] / "app" / "fixtures" / "demo_city.json"


@pytest.fixture(scope="module")
def data() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class Inputs(NamedTuple):
    ctx: Context
    crews: list[Crew]
    jobs: list
    decisions: list
    clusters: list[Cluster]
    priorities: dict[str, Priority]


@pytest.fixture
def inputs(data: dict) -> Inputs:
    context.reset_scenario()
    reports = [Report.model_validate(r) for r in data["reports"]]
    grouped = clusters.build_clusters(reports)
    ctx = context.build_context(datetime.fromisoformat(data["now"]))
    scores = {
        c.id: priority.score(
            c, [r for r in reports if r.id in c.report_ids], reports, ctx
        )
        for c in grouped
    }
    suspicious = next(
        c.id for c in grouped if data["expect"]["suspicious_report"] in c.report_ids
    )
    scores[suspicious] = scores[suspicious].model_copy(update={"needs_review": True})
    crews = [Crew.model_validate(c) for c in data["crews"]]
    jobs, decisions = make_jobs(grouped, scores, ctx)
    return Inputs(ctx, crews, jobs, decisions, grouped, scores)


def test_fixture_cluster_count_sanity(data: dict, inputs: Inputs) -> None:
    """Здравая проверка: B3 действительно даёт expect.clusters кластеров на этой fixture."""
    assert len(inputs.clusters) == data["expect"]["clusters"]


def test_batching_and_route_constraints(data: dict, inputs: Inputs) -> None:
    """Критерий 1: batching + expect.jobs_after_batching/site_batch; критерии 6, 7."""
    jobs, crews, ctx = inputs.jobs, inputs.crews, inputs.ctx
    assert len(jobs) == data["expect"]["jobs_after_batching"] == 9
    batch = next(j for j in jobs if "cl_r007" in j.cluster_ids)
    assert set(batch.cluster_ids) == {
        f"cl_{rid}" for rid in data["expect"]["site_batch"]
    }
    assert batch.service_min == 144
    suspicious_cluster = next(
        c.id
        for c in inputs.clusters
        if data["expect"]["suspicious_report"] in c.report_ids
    )
    assert all(suspicious_cluster not in j.cluster_ids for j in jobs)
    assert any(d.subject_id == suspicious_cluster for d in inputs.decisions)

    plan = solve(jobs, crews, ctx)
    assert plan == solve(jobs, crews, ctx)  # критерий 5 (детерминированность)
    assert plan.total_priority >= plan.baseline_total_priority  # критерий 7
    by_id = {j.id: j for j in jobs}
    for route in plan.routes:
        crew = next(c for c in crews if c.id == route.crew_id)
        for stop in route.stops:
            assert by_id[stop.job_id].skill in crew.skills  # критерий 6
            assert crew.shift_start <= stop.arrival <= stop.departure <= crew.shift_end


def test_deadline_and_short_shifts(inputs: Inputs) -> None:
    """Критерий 2: дедлайн; критерий 9: короткая смена -> unassigned с Decision."""
    jobs, crews, ctx = inputs.jobs, inputs.crews, inputs.ctx
    deadline_job = jobs[0].model_copy(update={"deadline": ctx.now})
    plan = solve([deadline_job], crews, ctx)
    assert deadline_job.id in plan.unassigned
    assert any(d.subject_id == deadline_job.id for d in plan.decisions)

    short = [
        c.model_copy(update={"shift_end": c.shift_start + timedelta(hours=2)})
        for c in crews
    ]
    plan = solve(jobs, short, ctx)
    assert plan.unassigned
    assert set(plan.unassigned) <= {d.subject_id for d in plan.decisions}


def test_replan_preserves_done_and_changes_skill(inputs: Inputs) -> None:
    """Критерий 3: replan needs_other_skill; критерий 4: replan not_found."""
    jobs, crews, ctx = inputs.jobs, inputs.crews, inputs.ctx
    plan = solve(jobs, crews, ctx)
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
    updated = replan(plan, update, jobs, crews, ctx)
    assert updated.version == plan.version + 1
    assert updated.status == "draft"
    assert next(r for r in updated.routes if r.crew_id == "c1").stops[0] == stable
    assert any(
        s.job_id == failed.job_id
        for r in updated.routes
        if r.crew_id == "c2"
        for s in r.stops
    )

    not_found = replan(
        plan, update.model_copy(update={"reason": "not_found"}), jobs, crews, ctx
    )
    assert any(d.kind == "review" for d in not_found.decisions)
    assert all(s.job_id != failed.job_id for r in not_found.routes for s in r.stops)


def test_storm_boosts_tree_and_keeps_it_in_plan(inputs: Inputs) -> None:
    """Критерий 8 (часть 2): storm повышает приоритет tree, задача остаётся в плане."""
    crews = inputs.crews
    context.set_scenario("storm")
    try:
        storm = context.build_context(inputs.ctx.now)
        jobs, decisions = make_jobs(inputs.clusters, inputs.priorities, storm)
        assert any(d.kind == "boost" for d in decisions)
        tree = next(j for j in jobs if j.skill == "green")
        assert any(
            s.job_id == tree.id
            for r in solve(jobs, crews, storm).routes
            for s in r.stops
        )
    finally:
        context.reset_scenario()


@pytest.mark.xfail(
    reason=(
        "Известный дефект вне путей B6: app/blocks/context/l0.py::_category() (блок B5) "
        "не распознаёт категорию 'pothole' по Job — там нет поля category, а cluster_ids "
        "у Job это id кластеров вида 'cl_r0XX' (так их создаёт B3), а не сырые id обращений, "
        "которыми проиндексирован rep_map. В итоге правило defer_potholes ни разу не "
        "срабатывает при storm: ямы получают 'param' (slow) вместо 'defer' и остаются в плане. "
        "Чинить нужно в B5 (context/l0.py) или согласовать формат id с B3 — оба файла вне "
        "разрешённых путей B6. См. Отчёт B6 в docs/status/B6.md."
    ),
    strict=True,
)
def test_storm_defers_potholes(inputs: Inputs) -> None:
    """Критерий 8 (часть 1): storm — ямы уходят из плана с Decision(kind='defer')."""
    context.set_scenario("storm")
    try:
        storm = context.build_context(inputs.ctx.now)
        jobs, decisions = make_jobs(inputs.clusters, inputs.priorities, storm)
        potholes = {c.id for c in inputs.clusters if c.category == "pothole"}
        assert all(not potholes.intersection(j.cluster_ids) for j in jobs)
        assert any(d.kind == "defer" for d in decisions)
    finally:
        context.reset_scenario()


def test_greedy_beats_naive_baseline_when_shift_is_constrained() -> None:
    """Критерий 7 (строго): под ограничением смены greedy по priority/service_min
    выигрывает у baseline (порядок поступления); мутация «всегда baseline» красит тест."""
    from app.contracts.models import Job

    crew = Crew.model_validate(
        {
            "id": "solo",
            "name": "Solo",
            "skills": ["road"],
            "start": {"lat": 47.0, "lon": 28.8},
            "shift_start": datetime(2026, 9, 26, 8, tzinfo=UTC),
            "shift_end": datetime(2026, 9, 26, 9, tzinfo=UTC),  # ровно 60 минут
        }
    )
    early_low_priority = Job(
        id="job_early_low",
        cluster_ids=["c1"],
        location={"lat": 47.0, "lon": 28.8},
        skill="road",
        service_min=50,
        priority=10,
    )
    late_high_priority = Job(
        id="job_late_high",
        cluster_ids=["c2"],
        location={"lat": 47.0, "lon": 28.8},
        skill="road",
        service_min=50,
        priority=100,
    )
    ctx = Context(now=datetime(2026, 9, 26, 8, tzinfo=UTC))
    plan = solve([early_low_priority, late_high_priority], [crew], ctx)
    assert plan.total_priority == 100
    assert plan.baseline_total_priority == 10
    assert plan.total_priority > plan.baseline_total_priority


def test_router_vroom_without_key_falls_back_to_greedy(
    monkeypatch: pytest.MonkeyPatch, inputs: Inputs
) -> None:
    """Критерий 10: ROUTER=vroom без ORS_API_KEY -> план строится, engine='greedy'."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ROUTER", "vroom")
    monkeypatch.setattr(settings, "ORS_API_KEY", None)
    plan = solve(inputs.jobs, inputs.crews, inputs.ctx)
    assert plan.engine == "greedy"


def test_baseline_total_priority_matches_naive_order(inputs: Inputs) -> None:
    """baseline_total_priority — тот же greedy на смене, но задачи в порядке поступления."""
    baseline = baseline_total_priority(inputs.jobs, inputs.crews)
    plan = solve(inputs.jobs, inputs.crews, inputs.ctx)
    assert baseline == plan.baseline_total_priority


def test_edge_cases_empty_and_single() -> None:
    """Границы данных: пустой список задач/бригад, один элемент, дубль id."""
    assert solve([], [], Context(now=datetime.now(UTC))).routes == []
    assert baseline_total_priority([], []) == 0

    crew = Crew.model_validate(
        {
            "id": "solo",
            "name": "Solo",
            "skills": ["road"],
            "start": {"lat": 47.0, "lon": 28.8},
            "shift_start": datetime(2026, 9, 26, 8, tzinfo=UTC),
            "shift_end": datetime(2026, 9, 26, 16, tzinfo=UTC),
        }
    )
    ctx = Context(now=datetime(2026, 9, 26, 8, tzinfo=UTC))
    plan = solve([], [crew], ctx)
    assert plan.routes[0].crew_id == "solo"
    assert plan.routes[0].stops == []

    from app.contracts.models import Job

    dup_job = Job(
        id="dup",
        cluster_ids=["c1"],
        location={"lat": 47.0, "lon": 28.8},
        skill="road",
        service_min=10,
        priority=10,
    )
    with pytest.raises(ValueError, match="Duplicate"):
        solve([dup_job, dup_job.model_copy()], [crew], ctx)

    zero_job = dup_job.model_copy(update={"service_min": 0})
    with pytest.raises(ValueError, match="positive"):
        solve([zero_job], [crew], ctx)
