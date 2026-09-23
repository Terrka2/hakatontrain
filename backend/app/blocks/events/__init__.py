"""Блок X1 · Мероприятия (дополнительный). Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/X1_events.md. Реализация: l0.py (заглушка), l1.py (D1), l2.py (внешний API).
"""

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException

from app.blocks.events import l0, l1, l2
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
    if settings.USE_MOCK:
        return l0.get_events(start, end)

    # 1. Попытка L2 (внешний API)
    try:
        events = l2.fetch_external_events(start, end)
        if events:
            return events
        log.warning(
            "X1: L2 fetch_external_events returned empty list, falling back to L1",
            exc_info=False,
        )
    except Exception:
        log.warning(
            "X1: L2 fetch_external_events failed, falling back to L1", exc_info=True
        )

    # 2. Попытка L1 (БД через репозиторий D1)
    try:
        events = l1.get_events(start, end, repo=repo)
        if events:
            return events
        log.warning(
            "X1: L1 get_events returned empty list, falling back to L0", exc_info=False
        )
    except HTTPException:
        raise
    except Exception:
        log.warning("X1: L1 get_events failed, falling back to L0", exc_info=True)

    # 3. Откат на L0 (демо-фикстура)
    return l0.get_events(start, end)


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
