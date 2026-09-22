"""Блок B8 · Работа бригад: маршрут, статусы, «не могу». Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B8_fieldwork.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

import logging
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

from app.blocks.fieldwork import l0, l1
from app.contracts.models import CrewRoute, JobUpdate, RouteStop
from app.core.config import settings

log = logging.getLogger(__name__)


def _call[T](
    op: str, l1_fn: Callable[..., T], l0_fn: Callable[..., T], *args: Any
) -> T:
    if settings.USE_MOCK:
        return l0_fn(*args)
    try:
        return l1_fn(*args)
    except HTTPException:
        raise
    except Exception:
        log.warning("B8: L1 %s failed, falling back to L0", op, exc_info=True)
        return l0_fn(*args)


def get_crew_route(crew_id: str) -> CrewRoute | None:
    return _call("get_crew_route", l1.get_crew_route, l0.get_crew_route, crew_id)


def apply_update(update: JobUpdate) -> RouteStop:
    return _call("apply_update", l1.apply_update, l0.apply_update, update)


def progress(plan_id: str) -> dict[str, dict[str, int]]:
    return _call("progress", l1.progress, l0.progress, plan_id)
