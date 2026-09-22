"""Блок X1 · Мероприятия (дополнительный). Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/X1_events.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from datetime import datetime

from app.blocks.events import l0
from app.contracts.models import Cluster, Context, Decision, Event, Job


def get_events(start: datetime, end: datetime) -> list[Event]:
    return l0.get_events(start, end)


def enrich_context(ctx: Context) -> Context:
    return l0.enrich_context(ctx)


def apply_deadlines(
    jobs: list[Job], clusters: list[Cluster], events: list[Event]
) -> tuple[list[Job], list[Decision]]:
    return l0.apply_deadlines(jobs, clusters, events)
