"""Блок B1 · Парсер и импорт обращений. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B1_ingest.md. Реализация: l0.py (без сети, fixture), l1.py (парсер/маппинг), l2.py (геокодирование B2).
"""

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.contracts.models import Report
from app.core.config import settings

from . import l0, l1, l2

log = logging.getLogger(__name__)


class IngestResult(BaseModel):
    reports: list[Report]
    rejected: list[dict[str, object]]  # {"row": int, "reason": str}


def load_fixture() -> list[Report]:
    """Загрузка обращений из demo_city.json."""
    return l0.load_fixture()


def parse_file(path: Path, mapping: dict[str, str] | None = None) -> IngestResult:
    """Парсинг файла (CSV/JSON).

    При USE_MOCK=true -> L0;
    Иначе если доступен geocoder B2 -> L2 (с откатом на L1 и L0);
    Иначе -> L1 (с откатом на L0).
    """
    if settings.USE_MOCK:
        reports, rejected = l0.parse_file(path, mapping)
        return IngestResult(reports=reports, rejected=rejected)

    if l2.is_geocoder_available():
        try:
            reports, rejected = l2.parse_file(path, mapping)
            return IngestResult(reports=reports, rejected=rejected)
        except Exception:  # noqa: BLE001
            log.warning("B1: L2 parse_file failed, falling back to L1", exc_info=True)

    try:
        reports, rejected = l1.parse_file(path, mapping)
        return IngestResult(reports=reports, rejected=rejected)
    except Exception:  # noqa: BLE001
        log.warning("B1: L1 parse_file failed, falling back to L0", exc_info=True)
        reports, rejected = l0.parse_file(path, mapping)
        return IngestResult(reports=reports, rejected=rejected)


def normalize(raw: dict[str, Any], mapping: dict[str, str] | None = None) -> Report:
    """Приведение сырой строки к Report.

    При USE_MOCK=true -> L0;
    Иначе если доступен geocoder B2 -> L2 (с откатом на L1 и L0);
    Иначе -> L1 (с откатом на L0).
    """
    if settings.USE_MOCK:
        return l0.normalize(raw, mapping or {})

    if l2.is_geocoder_available():
        try:
            return l2.normalize(raw, mapping)
        except Exception:  # noqa: BLE001
            log.warning("B1: L2 normalize failed, falling back to L1", exc_info=True)

    try:
        return l1.normalize(raw, mapping)
    except Exception:  # noqa: BLE001
        log.warning("B1: L1 normalize failed, falling back to L0", exc_info=True)
        return l0.normalize(raw, mapping or {})
