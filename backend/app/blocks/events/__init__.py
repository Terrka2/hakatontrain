"""Блок X1 · Мероприятия (дополнительный). Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/X1_events.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException

from app.blocks.events import l0, l1
from app.contracts.models import Cluster, Context, Decision, Event, Job
from app.core.config import settings

log = logging.getLogger(__name__)


def _call[T](
    op: str, l1_fn: Callable[..., T], l0_fn: Callable[..., T], *args: Any, **kwargs: Any
) -> T:
    if settings.USE_MOCK:
        return l0_fn(*args, **kwargs)
    try:
        return l1_fn(*args, **kwargs)
    except HTTPException:
        raise
    except Exception:
        log.warning("X1: L1 %s failed, falling back to L0", op, exc_info=True)
        return l0_fn(*args, **kwargs)


def get_events(start: datetime, end: datetime, repo: Any = None) -> list[Event]:
    return _call("get_events", l1.get_events, l0.get_events, start, end, repo=repo)


def add_event(event: Event, repo: Any = None) -> Event:
    return _call("add_event", l1.add_event, l0.add_event, event, repo=repo)


def enrich_context(ctx: Context) -> Context:
    if settings.OPTIONAL_BLOCKS != "on":
        ctx.events = []
        return ctx
    ctx.events = get_events(ctx.now, ctx.now + timedelta(hours=72))
    return ctx


def apply_deadlines(
    jobs: list[Job], clusters: list[Cluster], events: list[Event]
) -> tuple[list[Job], list[Decision]]:
    return l0.apply_deadlines(jobs, clusters, events)
