"""Блок B7 · Навигатор жителя (дополнительный). Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B7_navigator.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from app.contracts.models import Cluster, Event, Priority, Trip, TripRequest

HAZARD_BUFFER_M = 40


def plan_trip(
    req: TripRequest,
    clusters: list[Cluster],
    priorities: dict[str, Priority],
    events: list[Event],
) -> Trip:
    raise NotImplementedError(
        "B7: реализуй по контракту docs/contracts/B7_navigator.md"
    )
