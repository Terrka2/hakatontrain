"""Блок <ID> · <Название>. Порт блока — только функции, объявленные здесь.

Контракт: docs/contracts/<ID>_example.md. Реализация: l0.py (без сети), l1.py (целевой уровень).
Файл создан каркасом C0: тела функций заменяются, сигнатуры — нет.
"""

import logging

from app.contracts.models import Cluster, Context, Priority, Report
from app.core.config import settings

from . import l0, l1

log = logging.getLogger(__name__)


def score(cluster: Cluster, reports: list[Report], ctx: Context) -> Priority:
    """Единая точка входа. Уровень выбирается переключателем из контракта (здесь — USE_MOCK)."""
    if settings.USE_MOCK:
        return l0.score(cluster, reports, ctx)
    try:
        return l1.score(cluster, reports, ctx)
    except Exception:  # noqa: BLE001 — любая ошибка L1 = тихий откат на L0, не падение
        log.warning("<ID>: L1 failed, falling back to L0", exc_info=True)
        return l0.score(cluster, reports, ctx)
