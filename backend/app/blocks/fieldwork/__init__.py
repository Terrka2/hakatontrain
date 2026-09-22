"""Блок B8 · Работа бригад: маршрут, статусы, «не могу». Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B8_fieldwork.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from app.blocks.fieldwork import l0
from app.contracts.models import CrewRoute, JobUpdate, RouteStop


def get_crew_route(crew_id: str) -> CrewRoute | None:
    return l0.get_crew_route(crew_id)


def apply_update(update: JobUpdate) -> RouteStop:
    return l0.apply_update(update)


def progress(plan_id: str) -> dict[str, dict[str, int]]:
    return l0.progress(plan_id)
