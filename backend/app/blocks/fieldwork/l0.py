"""Уровень L0 блока B8: маршруты бригад и обновление статусов в памяти на fixture demo_city.json."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import HTTPException

from app.contracts import models

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "demo_city.json"

_plan: models.Plan | None = None
_clusters: dict[str, models.Cluster] = {}
_reports: dict[str, models.Report] = {}
_jobs: dict[str, models.Job] = {}


def reset_state() -> None:
    """Сброс состояния в исходное на основе demo_city.json."""
    global _plan, _clusters, _reports, _jobs
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        data = json.load(f)

    _reports = {r["id"]: models.Report(**r) for r in data.get("reports", [])}
    t0 = datetime(2026, 9, 22, 8, 0, tzinfo=UTC)
    t_arr, t_dep = t0.replace(day=26, minute=30), t0.replace(day=26, hour=9)

    specs = [
        ("c1", "job_c1_1", "cl_001", "pothole", ["r001", "r002", "r003"], "road"),
        (
            "c1",
            "job_c1_2",
            "cl_batch",
            "pothole",
            ["r007", "r008", "r009", "r010"],
            "road",
        ),
        ("c2", "job_c2_1", "cl_004", "streetlight", ["r004"], "electric"),
        ("c2", "job_c2_2", "cl_014", "tree", ["r014"], "green"),
    ]
    _clusters, _jobs = {}, {}
    for _, j, c, cat, r, sk in specs:
        loc = _reports[r[0]].location
        _clusters[c] = models.Cluster(
            id=c,
            category=cat,
            centroid=loc,
            report_ids=r,
            first_reported_at=t0,
            last_reported_at=t0,
        )
        _jobs[j] = models.Job(
            id=j, cluster_ids=[c], location=loc, skill=sk, service_min=30, priority=70
        )

    _plan = models.Plan(
        id="plan_demo",
        day=date(2026, 9, 26),
        routes=[
            models.CrewRoute(
                crew_id=c,
                stops=[
                    models.RouteStop(
                        job_id=j,
                        location=_jobs[j].location,
                        arrival=t_arr,
                        departure=t_dep,
                    )
                    for crw, j, *_ in specs
                    if crw == c
                ],
            )
            for c in ("c1", "c2", "c3")
        ],
        status="approved",
        version=1,
    )


reset_state()


def set_plan(plan: models.Plan | None) -> None:
    global _plan
    _plan = plan


def get_cluster(cluster_id: str) -> models.Cluster | None:
    return _clusters.get(cluster_id)


def get_report(report_id: str) -> models.Report | None:
    return _reports.get(report_id)


def get_crew_route(crew_id: str) -> models.CrewRoute | None:
    """Маршрут бригады только из плана со status='approved'."""
    if not _plan or _plan.status != "approved":
        return None
    for r in _plan.routes:
        if r.crew_id == crew_id:
            return r.model_copy(deep=True)
    return None


def validate_update(route_crew_id: str, curr: str, update: models.JobUpdate) -> None:
    if update.crew_id != route_crew_id:
        raise HTTPException(
            403, f"Бригада {update.crew_id} не может менять остановку {route_crew_id}"
        )
    nxt = update.status
    if not (
        (curr == "pending" and nxt != "done")
        or (curr == "arrived" and nxt != "arrived")
    ):
        raise HTTPException(409, f"Недопустимый переход: {curr} -> {nxt}")
    if nxt == "done" and not (update.photo_url and update.photo_url.strip()):
        raise HTTPException(422, "Для done обязательно photo_url")
    if nxt == "failed" and not update.reason:
        raise HTTPException(422, "Для failed обязательно reason")
    if update.reason == "needs_other_skill" and not update.needs_skill:
        raise HTTPException(422, "Для needs_other_skill нужен needs_skill")


def trigger_operator(update: models.JobUpdate) -> None:
    from app.blocks import operator

    try:
        operator.operator_run("job_update", update.at, job_update=update)
    except NotImplementedError:
        pass


def apply_update(update: models.JobUpdate) -> models.RouteStop:
    """Применяет обновление статуса остановки, валидирует переход и побочные эффекты."""
    if not _plan or _plan.status != "approved":
        raise HTTPException(404, "План не найден")

    pair = [(r, s) for r in _plan.routes for s in r.stops if s.job_id == update.job_id]
    if not pair:
        raise HTTPException(404, f"Остановка {update.job_id} не найдена")
    route, stop = pair[0]
    validate_update(route.crew_id, stop.status, update)

    stop.status = update.status
    if update.status == "done" and update.job_id in _jobs:
        for cid in _jobs[update.job_id].cluster_ids:
            if c := _clusters.get(cid):
                c.status = "resolved"
                for rid in c.report_ids:
                    if r := _reports.get(rid):
                        r.status = "resolved"
    elif update.status == "failed":
        trigger_operator(update)
    return stop.model_copy(deep=True)


def progress(plan_id: str) -> dict[str, dict[str, int]]:
    """Прогресс выполнения плана: crew_id -> {'done': X, 'failed': Y, ...}."""
    if not _plan or _plan.id != plan_id:
        return {}
    st_keys = ("done", "failed", "pending", "arrived")
    return {
        r.crew_id: {st: sum(s.status == st for s in r.stops) for st in st_keys}
        for r in _plan.routes
    }
