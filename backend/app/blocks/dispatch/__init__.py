"""Блок B6 · Диспетчер: план и маршруты бригад. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B6_dispatch.md. Реализация: l0.py (ROUTER=greedy, целевой уровень — L0),
store.py (свой план и бригады в памяти, независимо от run-хранилища B0).
"""

from datetime import date, datetime

from app.blocks import clusters as clusters_block
from app.blocks import context as context_block
from app.blocks import ingest as ingest_block
from app.blocks import priority as priority_block
from app.contracts.models import (
    Cluster,
    Context,
    Crew,
    Decision,
    Job,
    JobUpdate,
    Plan,
    Priority,
)

from . import l0, store

BATCH_RADIUS_M = 450


def make_jobs(
    clusters: list[Cluster], priorities: dict[str, Priority], ctx: Context
) -> tuple[list[Job], list[Decision]]:
    return l0.make_jobs(clusters, priorities, ctx)


def solve(jobs: list[Job], crews: list[Crew], ctx: Context) -> Plan:
    return l0.solve(jobs, crews, ctx)


def replan(
    plan: Plan, update: JobUpdate, jobs: list[Job], crews: list[Crew], ctx: Context
) -> Plan:
    return l0.replan(plan, update, jobs, crews, ctx)


def baseline_total_priority(jobs: list[Job], crews: list[Crew]) -> int:
    return l0.baseline_total_priority(jobs, crews)


def get_crews() -> list[Crew]:
    """Бригады: только чтение из demo_city.json."""
    return store.load_crews()


def _now_for_day(day: date) -> datetime:
    """Время начала дня для построения Context: берёт tzinfo/час из demo_city.json."""
    fixture_now = store.fixture_now()
    if day == fixture_now.date():
        return fixture_now
    return fixture_now.replace(year=day.year, month=day.month, day=day.day)


def create_plan(day: date) -> Plan:
    """Строит новый черновик плана на день и сохраняет его в своём хранилище.

    Собирает весь конвейер сам (contract: B6 зависит от B2, B3, B4, B5): obращения (B1) ->
    кластеры (B3) -> приоритет (B4) -> контекст (B5) -> свои make_jobs/solve. Если сосед ещё
    не реализован (NotImplementedError), ошибка не глушится — роут отдаёт 503, а не 500.
    """
    reports = ingest_block.load_fixture()
    ctx = context_block.build_context(_now_for_day(day))
    grouped = clusters_block.build_clusters(reports)
    scores = {
        c.id: priority_block.score(
            c, [r for r in reports if r.id in c.report_ids], reports, ctx
        )
        for c in grouped
    }
    jobs, _ = make_jobs(grouped, scores, ctx)
    plan = solve(jobs, get_crews(), ctx).model_copy(update={"day": day})
    return store.record_plan(plan)


def record_plan(plan: Plan) -> Plan:
    """Сохраняет уже построенный план (например, результат replan) как новый черновик."""
    return store.record_plan(plan)


def get_plan(plan_id: str) -> Plan | None:
    return store.get(plan_id)


def get_draft_plan() -> Plan | None:
    return store.get_draft()


def get_current_plan() -> Plan | None:
    return store.get_current()


def approve_plan(plan_id: str, approved_by: str) -> Plan | None:
    return store.approve(plan_id, approved_by)
