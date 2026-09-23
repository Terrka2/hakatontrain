"""Deterministic greedy dispatch at 30 km/h, with skills and time windows."""

import math
from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from app.blocks.context import apply_weather_rules
from app.blocks.geo import centroid, haversine_m
from app.contracts.models import (
    CATEGORY_SERVICE_MIN,
    CATEGORY_TO_SKILL,
    Cluster,
    Context,
    Crew,
    CrewRoute,
    Decision,
    Job,
    JobUpdate,
    Plan,
    Priority,
    RouteStop,
)


def _decision(kind: str, subject: str, reason: str) -> Decision:
    return Decision(kind=kind, subject_id=subject, reason=reason, by="rule")


def make_jobs(
    clusters: list[Cluster], priorities: dict[str, Priority], ctx: Context
) -> tuple[list[Job], list[Decision]]:
    from . import BATCH_RADIUS_M

    pending = sorted(clusters, key=lambda c: (-priorities[c.id].score, c.id))
    jobs, decisions = [], []
    ready = []
    for cluster in pending:
        if priorities[cluster.id].needs_review:
            decisions.append(
                _decision("unassigned", cluster.id, "Требует проверки оператором")
            )
        else:
            ready.append(cluster)
    while ready:
        first = ready.pop(0)
        skill = CATEGORY_TO_SKILL[first.category]
        group = [first] + [
            c
            for c in ready
            if CATEGORY_TO_SKILL[c.category] == skill
            and haversine_m(first.centroid, c.centroid) <= BATCH_RADIUS_M
        ]
        ids = sorted(c.id for c in group)
        ready = [c for c in ready if c.id not in ids]
        duration = sum(CATEGORY_SERVICE_MIN[c.category] for c in group)
        job = Job(
            id="job_" + "_".join(ids),
            cluster_ids=ids,
            location=centroid([c.centroid for c in group]),
            skill=skill,
            service_min=round(duration * 0.8) if len(group) > 1 else duration,
            priority=round(max(priorities[c.id].score for c in group)),
        )
        jobs.append(job)
        if len(group) > 1:
            decisions.append(
                _decision(
                    "batch", job.id, "Объединены соседние проблемы: " + ", ".join(ids)
                )
            )
    # Baseline order is arrival order, independent of the greedy ratio ordering.
    first_seen = {c.id: c.first_reported_at for c in clusters}
    jobs.sort(key=lambda j: (min(first_seen[c] for c in j.cluster_ids), j.id))
    jobs, weather_decisions = apply_weather_rules(jobs, ctx.weather)
    return jobs, decisions + weather_decisions


def _schedule(jobs: list[Job], crews: list[Crew], ctx: Context) -> Plan:
    team = sorted(crews, key=lambda c: c.id)
    clocks = {c.id: max(c.shift_start, ctx.now) for c in team}
    locations = {c.id: c.start for c in team}
    routes = {c.id: CrewRoute(crew_id=c.id, stops=[], geometry=[c.start]) for c in team}
    unassigned, decisions = [], []
    total = 0
    for job in jobs:
        choices = []
        for crew in team:
            if job.skill not in crew.skills:
                continue
            travel = math.ceil(haversine_m(locations[crew.id], job.location) / 500)
            arrival = clocks[crew.id] + timedelta(minutes=travel)
            departure = arrival + timedelta(minutes=job.service_min)
            if departure <= crew.shift_end and (
                job.deadline is None or arrival <= job.deadline
            ):
                choices.append((travel, arrival, crew.id, departure))
        if not choices:
            unassigned.append(job.id)
            decisions.append(
                _decision(
                    "unassigned",
                    job.id,
                    "Нет бригады с нужным навыком и доступным временем до срока",
                )
            )
            continue
        travel, arrival, crew_id, departure = min(choices)
        route = routes[crew_id]
        route.stops.append(
            RouteStop(
                job_id=job.id,
                location=job.location,
                arrival=arrival,
                departure=departure,
            )
        )
        route.geometry.append(job.location)
        route.drive_min += travel
        route.work_min += job.service_min
        clocks[crew_id], locations[crew_id] = departure, job.location
        total += job.priority
    result = Plan(
        id="pending",
        day=ctx.now.date(),
        routes=list(routes.values()),
        unassigned=unassigned,
        total_priority=total,
        decisions=decisions,
    )
    result.id = "plan_" + uuid5(NAMESPACE_URL, result.model_dump_json()).hex[:16]
    return result


def solve(jobs: list[Job], crews: list[Crew], ctx: Context) -> Plan:
    if len({j.id for j in jobs}) != len(jobs) or len({c.id for c in crews}) != len(
        crews
    ):
        raise ValueError("Duplicate job or crew ids")
    if any(j.service_min <= 0 for j in jobs):
        raise ValueError("Job duration must be positive")
    baseline = _schedule(jobs, crews, ctx)
    ordered = sorted(jobs, key=lambda j: (-j.priority / j.service_min, j.id))
    greedy = _schedule(ordered, crews, ctx)
    result = greedy if greedy.total_priority >= baseline.total_priority else baseline
    result.baseline_total_priority = baseline.total_priority
    return result


def baseline_total_priority(jobs: list[Job], crews: list[Crew]) -> int:
    if not crews:
        return 0
    return _schedule(
        jobs, crews, Context(now=min(c.shift_start for c in crews))
    ).total_priority


def replan(
    plan: Plan, update: JobUpdate, jobs: list[Job], crews: list[Crew], ctx: Context
) -> Plan:
    if not any(
        r.crew_id == update.crew_id and any(s.job_id == update.job_id for s in r.stops)
        for r in plan.routes
    ):
        raise ValueError("Job update does not belong to this crew route")
    old = plan.model_copy(deep=True)
    for route in old.routes:
        for stop in route.stops:
            if route.crew_id == update.crew_id and stop.job_id == update.job_id:
                if stop.status not in {"done", "arrived"}:
                    stop.status = update.status
    fixed = {
        r.crew_id: [s for s in r.stops if s.status in {"done", "arrived"}]
        for r in old.routes
    }
    fixed_ids = {s.job_id for stops in fixed.values() for s in stops}
    remaining = [j.model_copy(deep=True) for j in jobs if j.id not in fixed_ids]
    decisions = [
        _decision("replan", update.job_id, "План перестроен после сообщения бригады")
    ]
    if update.status == "failed" and update.reason == "not_found":
        remaining = [j for j in remaining if j.id != update.job_id]
        decisions.append(
            _decision("review", update.job_id, "Бригада не нашла проблему")
        )
    elif update.status == "failed" and update.reason == "needs_other_skill":
        if not update.needs_skill:
            raise ValueError("needs_skill is required")
        remaining = [
            j.model_copy(update={"skill": update.needs_skill})
            if j.id == update.job_id
            else j
            for j in remaining
        ]
    shifted = []
    for crew in crews:
        stops = fixed.get(crew.id, [])
        shifted.append(
            crew.model_copy(
                update={
                    "start": stops[-1].location if stops else crew.start,
                    "shift_start": max(
                        crew.shift_start,
                        update.at,
                        stops[-1].departure if stops else update.at,
                    ),
                }
            )
        )
    effective = ctx.model_copy(update={"now": max(ctx.now, update.at)})
    result = solve(remaining, shifted, effective)
    if update.status == "failed" and update.reason in {"weather", "no_access", "other"}:
        deferred = sorted(
            remaining,
            key=lambda j: (j.id == update.job_id, -j.priority / j.service_min, j.id),
        )
        result = _schedule(deferred, shifted, effective)
    for route in result.routes:
        prefix = fixed.get(route.crew_id, [])
        route.stops = prefix + route.stops
        route.geometry = [s.location for s in prefix] + route.geometry
        route.work_min += sum(
            round((s.departure - s.arrival).total_seconds() / 60) for s in prefix
        )
    result.total_priority += sum(j.priority for j in jobs if j.id in fixed_ids)
    result.version = plan.version + 1
    result.decisions.extend(decisions)
    result.id = "plan_" + uuid5(NAMESPACE_URL, result.model_dump_json()).hex[:16]
    return result
