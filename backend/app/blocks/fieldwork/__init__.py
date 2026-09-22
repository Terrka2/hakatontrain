"""Блок B8 · Работа бригад: маршрут, статусы, «не могу». Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B8_fieldwork.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from app.contracts.models import CrewRoute, JobUpdate, RouteStop


def get_crew_route(crew_id: str) -> CrewRoute | None:
    raise NotImplementedError(
        "B8: реализуй по контракту docs/contracts/B8_fieldwork.md"
    )


def apply_update(update: JobUpdate) -> RouteStop:
    raise NotImplementedError(
        "B8: реализуй по контракту docs/contracts/B8_fieldwork.md"
    )


def progress(plan_id: str) -> dict[str, dict[str, int]]:
    raise NotImplementedError(
        "B8: реализуй по контракту docs/contracts/B8_fieldwork.md"
    )
