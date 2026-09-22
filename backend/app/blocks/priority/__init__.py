"""Блок B4 · Объяснимый приоритет. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B4_priority.md. Реализация: l0.py (без сети), l1.py (целевой уровень).
"""

import logging

from app.contracts.models import Cluster, Context, Priority, Report

from . import l0, l1

log = logging.getLogger(__name__)


def score(
    cluster: Cluster,
    reports: list[Report],
    history: list[Report],
    ctx: Context,
    weights: dict[str, float] | None = None,
) -> Priority:
    """Вычисляет объяснимый приоритет кластера с тихим откатом на L0 при ошибках."""
    try:
        return l1.score(cluster, reports, history, ctx, weights)
    except Exception:  # noqa: BLE001
        log.warning("B4: L1 failed, falling back to L0", exc_info=True)
        return l0.score(cluster, reports, history, ctx, weights)
