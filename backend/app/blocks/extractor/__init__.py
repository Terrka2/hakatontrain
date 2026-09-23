"""Блок L1 · LLM: извлечение признаков и проверка на нейрослоп. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/L1_extractor.md. Реализация: l0.py (словари сигналов RU/RO, без сети),
l1.py (LLM через backend/app/llm).
"""

import logging

from app.contracts.models import Extracted, Report, Verification
from app.core.config import settings

from . import l0, l1

log = logging.getLogger(__name__)


def extract(report: Report) -> Extracted:
    """Единая точка входа. Уровень выбирается переключателем LLM=off|on."""
    if settings.LLM == "off":
        return l0.extract(report)
    try:
        return l1.extract(report)
    except Exception:  # noqa: BLE001 — любая ошибка L1 = тихий откат на L0, не падение
        log.warning(
            "L1(extractor): extract L1 failed, falling back to L0", exc_info=True
        )
        return l0.extract(report)


def verify(report: Report, nearby: list[Report]) -> Verification:
    """Единая точка входа. Уровень выбирается переключателем LLM=off|on."""
    if settings.LLM == "off":
        return l0.verify(report, nearby)
    try:
        return l1.verify(report, nearby)
    except Exception:  # noqa: BLE001 — любая ошибка L1 = тихий откат на L0, не падение
        log.warning(
            "L1(extractor): verify L1 failed, falling back to L0", exc_info=True
        )
        return l0.verify(report, nearby)
