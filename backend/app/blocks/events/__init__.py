"""Блок X1 · Мероприятия (дополнительный). Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/X1_events.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from datetime import datetime

from app.contracts.models import Cluster, Context, Decision, Event, Job


def get_events(start: datetime, end: datetime) -> list[Event]:
    raise NotImplementedError("X1: реализуй по контракту docs/contracts/X1_events.md")


def enrich_context(ctx: Context) -> Context:
    raise NotImplementedError("X1: реализуй по контракту docs/contracts/X1_events.md")


def apply_deadlines(
    jobs: list[Job], clusters: list[Cluster], events: list[Event]
) -> tuple[list[Job], list[Decision]]:
    raise NotImplementedError("X1: реализуй по контракту docs/contracts/X1_events.md")
