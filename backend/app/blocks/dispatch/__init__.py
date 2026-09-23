"""Блок B6 · Диспетчер: план и маршруты бригад. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B6_dispatch.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

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

from . import l0

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
