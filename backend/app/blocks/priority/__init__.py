"""Блок B4 · Объяснимый приоритет. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B4_priority.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from app.contracts.models import Cluster, Context, Priority, Report


def score(
    cluster: Cluster,
    reports: list[Report],
    history: list[Report],
    ctx: Context,
    weights: dict[str, float] | None = None,
) -> Priority:
    raise NotImplementedError("B4: реализуй по контракту docs/contracts/B4_priority.md")
