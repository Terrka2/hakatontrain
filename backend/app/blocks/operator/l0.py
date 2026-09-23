"""B0 orchestration only. Neighbouring ports own all business calculations."""

import json
import logging
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, Literal

from app.blocks import clusters, context, dispatch, extractor, ingest, priority
from app.contracts.models import (
    ClusterDetail,
    ClusterOut,
    Crew,
    Decision,
    JobUpdate,
    OperatorRun,
    Plan,
    Report,
)

if TYPE_CHECKING:
    from . import PipelineResult

log = logging.getLogger(__name__)
_lock = RLock()
_clusters: dict[str, ClusterDetail] = {}
_reviews: dict[str, Literal["accept", "reject"]] = {}
_plans: dict[str, Plan] = {}
_runs: list[OperatorRun] = []


def _error(stage: str) -> Decision:
    log.warning("B0: %s failed", stage, exc_info=True)
    return Decision(
        kind="defer",
        subject_id=stage,
        reason=f"Ошибка {stage}; план не создан",
        by="rule",
    )


def _pipeline(
    reports: list[Report], now: datetime
) -> tuple[PipelineResult, list[Decision], list[Report]]:
    from . import PipelineResult

    if now.utcoffset() is None or len({r.id for r in reports}) != len(reports):
        raise ValueError("Expected timezone-aware now and unique report ids")
    prepared = [r.model_copy(deep=True) for r in reports]
    for report in prepared:
        report.extracted = extractor.extract(report)
    for report in prepared:
        report.verification = extractor.verify(report, prepared)
    grouped = clusters.build_clusters(prepared)
    ctx = context.build_context(now)
    scores, errors = {}, []
    for cluster in grouped:
        try:
            value = priority.score(
                cluster,
                [r for r in prepared if r.id in cluster.report_ids],
                prepared,
                ctx,
            )
            if cluster.id in _reviews:
                value = value.model_copy(update={"needs_review": False})
            scores[cluster.id] = value
        except Exception:
            errors.append(_error("B4"))
            break
    return (
        PipelineResult(clusters=grouped, priorities=scores, context=ctx),
        errors,
        prepared,
    )


def run_pipeline(reports: list[Report], now: datetime) -> PipelineResult:
    with _lock:
        return _pipeline(reports, now)[0]


def operator_run(
    trigger: str, now: datetime, job_update: JobUpdate | None = None
) -> OperatorRun:
    if trigger not in {"manual", "import", "new_report", "weather", "job_update"}:
        raise ValueError("Unknown operator trigger")
    if now.utcoffset() is None or (trigger == "job_update" and job_update is None):
        raise ValueError("Expected timezone-aware now and a job update for job_update")
    with _lock:
        reports = ingest.load_fixture()
        result, decisions, prepared = _pipeline(reports, now)
        fresh = {c.id for c in result.clusters} - _clusters.keys()
        _clusters.clear()
        _clusters.update(
            {
                c.id: ClusterDetail(
                    **c.model_dump(),
                    priority=result.priorities.get(c.id),
                    reports=[r for r in prepared if r.id in c.report_ids],
                )
                for c in result.clusters
            }
        )
        plan = None
        if not decisions:
            try:
                eligible = [
                    c for c in result.clusters if _reviews.get(c.id) != "reject"
                ]
                jobs, job_decisions = dispatch.make_jobs(
                    eligible, result.priorities, result.context
                )
                decisions.extend(job_decisions)
                fixture = json.loads(
                    (
                        Path(__file__).resolve().parents[2] / "fixtures/demo_city.json"
                    ).read_text(encoding="utf-8")
                )
                crews = [Crew.model_validate(c) for c in fixture["crews"]]
                if trigger == "job_update":
                    previous = next(
                        (r.plan_id for r in reversed(_runs) if r.plan_id), None
                    )
                    if previous is None:
                        raise ValueError("No previous plan")
                    plan = dispatch.replan(
                        _plans[previous].model_copy(deep=True),
                        job_update,
                        jobs,
                        crews,
                        result.context,
                    )
                else:
                    plan = dispatch.solve(jobs, crews, result.context)
                plan = plan.model_copy(
                    deep=True,
                    update={
                        "id": f"operator-plan-{len(_runs) + 1}",
                        "version": len(_runs) + 1,
                        "status": "draft",
                        "approved_by": None,
                    },
                )
                decisions.extend(plan.decisions)
                _plans[plan.id] = plan
            except Exception:
                decisions.append(_error("B6"))
                plan = None
        review = sorted(
            c.id
            for c in result.clusters
            if result.priorities.get(c.id) is None
            or result.priorities[c.id].needs_review
        )
        run = OperatorRun(
            id=f"operator-run-{len(_runs) + 1}",
            trigger=trigger,
            at=now,
            reports_seen=len(reports),
            clusters_total=len(result.clusters),
            clusters_new=len(fresh),
            needs_review=review,
            plan_id=plan.id if plan else None,
            decisions=decisions,
            summary=f"Разобрано {len(reports)} обращений → {len(result.clusters)} проблем ({len(fresh)} новых). На проверку: {', '.join(review) or 'нет'}. План {f'v{plan.version}: черновик' if plan else 'не создан'}.",
        )
        _runs.append(run.model_copy(deep=True))
        return run


def get_clusters(
    category: str | None = None, min_score: float | None = None
) -> list[ClusterOut]:
    with _lock:
        _ensure_loaded()
        rows = [
            ClusterOut(**c.model_dump(exclude={"reports"}))
            for c in _clusters.values()
            if (not category or c.category == category)
            and (
                min_score is None
                or (c.priority is not None and c.priority.score >= min_score)
            )
        ]
        return sorted(
            rows, key=lambda c: (-(c.priority.score if c.priority else -1), c.id)
        )


def get_cluster(cluster_id: str) -> ClusterDetail | None:
    with _lock:
        _ensure_loaded()
        row = _clusters.get(cluster_id)
        return row.model_copy(deep=True) if row else None


def review_cluster(
    cluster_id: str, decision: Literal["accept", "reject"]
) -> ClusterDetail | None:
    with _lock:
        _ensure_loaded()
        row = _clusters.get(cluster_id)
        if row is None:
            return None
        _reviews[cluster_id] = decision
        if row.priority is not None:
            row.priority = row.priority.model_copy(update={"needs_review": False})
        return row.model_copy(deep=True)


def get_runs(limit: int = 20) -> list[OperatorRun]:
    with _lock:
        return [
            r.model_copy(deep=True)
            for _, r in sorted(
                enumerate(_runs), key=lambda item: (item[1].at, item[0]), reverse=True
            )[:limit]
        ]


def get_plan(plan_id: str) -> Plan | None:
    with _lock:
        plan = _plans.get(plan_id)
        return plan.model_copy(deep=True) if plan else None


def _ensure_loaded() -> None:
    if not _runs:
        operator_run("manual", fixture_now())


def fixture_now() -> datetime:
    """L0 uses the fixture's simulation clock, matching its reports and shifts."""
    fixture = json.loads(
        (Path(__file__).resolve().parents[2] / "fixtures/demo_city.json").read_text(
            encoding="utf-8"
        )
    )
    return datetime.fromisoformat(fixture["now"])
