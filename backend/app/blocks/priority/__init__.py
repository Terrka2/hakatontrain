"""Блок B4 · Объяснимый приоритет. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B4_priority.md. Реализация: l0.py (чистая математика HZ, DM, AG, FL).
"""

from app.contracts.models import Cluster, Context, Priority, Report

from . import l0


def score(
    cluster: Cluster,
    reports: list[Report],
    history: list[Report],
    ctx: Context,
    weights: dict[str, float] | None = None,
) -> Priority:
    """Вычисляет объяснимый приоритет кластера."""
    return l0.score(cluster, reports, history, ctx, weights)
