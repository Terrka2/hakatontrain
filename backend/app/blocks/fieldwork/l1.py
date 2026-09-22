"""Уровень L1 блока B8: работа через репозиторий D1."""

from fastapi import HTTPException

from app.blocks.fieldwork import l0
from app.contracts import models
from app.db import Repository, get_repository


def get_crew_route(
    crew_id: str, repo: Repository | None = None
) -> models.CrewRoute | None:
    plan = (repo or get_repository()).current_plan(status="approved")
    if not plan:
        return None
    for route in plan.routes:
        if route.crew_id == crew_id:
            return route.model_copy(deep=True)
    return None


def apply_update(
    update: models.JobUpdate, repo: Repository | None = None
) -> models.RouteStop:
    r = repo or get_repository()
    plan = r.current_plan(status="approved")
    if not plan:
        raise HTTPException(404, "План не найден")

    pair = [
        (route, s)
        for route in plan.routes
        for s in route.stops
        if s.job_id == update.job_id
    ]
    if not pair:
        raise HTTPException(404, f"Остановка {update.job_id} не найдена")
    route, stop = pair[0]
    l0.validate_update(route.crew_id, stop.status, update)

    r.set_stop_status(plan.id, update.job_id, update.status)
    stop.status = update.status

    if update.status == "done":
        job = l0._jobs.get(update.job_id)
        job_cids = job.cluster_ids if job else [update.job_id]
        clusters_to_save: list[models.Cluster] = []
        priorities_to_save: dict[str, models.Priority] = {}
        for c, p in r.list_clusters():
            if c.id in job_cids:
                c.status = "resolved"
                clusters_to_save.append(c)
                if p:
                    priorities_to_save[c.id] = p
        if clusters_to_save:
            r.save_clusters(clusters_to_save, priorities_to_save)
            all_rids = {rid for c in clusters_to_save for rid in c.report_ids}
            reps = [
                rep.model_copy(update={"status": "resolved"})
                for rep in r.list_reports()
                if rep.id in all_rids
            ]
            if reps:
                r.upsert_reports(reps)
    elif update.status == "failed":
        l0.trigger_operator(update)

    return stop.model_copy(deep=True)


def progress(plan_id: str, repo: Repository | None = None) -> dict[str, dict[str, int]]:
    r = repo or get_repository()
    p = r.get_plan(plan_id)
    if not p:
        cp = r.current_plan()
        p = cp if cp and cp.id == plan_id else None
    if not p:
        return {}
    st_keys = ("done", "failed", "pending", "arrived")
    return {
        route.crew_id: {st: sum(s.status == st for s in route.stops) for st in st_keys}
        for route in p.routes
    }
