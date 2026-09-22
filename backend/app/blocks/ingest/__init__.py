"""Блок B1 · Парсер и импорт обращений. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B1_ingest.md. Реализация: l0.py (без сети, fixture), l1.py (целевой уровень).
"""

import logging
from pathlib import Path

from pydantic import BaseModel

from app.contracts.models import Report
from app.core.config import settings

from . import l0, l1

log = logging.getLogger(__name__)


class IngestResult(BaseModel):
    reports: list[Report]
    rejected: list[dict[str, object]]  # {"row": int, "reason": str}


def load_fixture() -> list[Report]:
    """Загрузка обращений из demo_city.json."""
    return l0.load_fixture()


def parse_file(path: Path, mapping: dict[str, str] | None = None) -> IngestResult:
    """Парсинг файла (CSV/JSON). При USE_MOCK или ошибке L1 — тихий откат на L0."""
    if settings.USE_MOCK:
        reports, rejected = l0.parse_file(path, mapping)
        return IngestResult(reports=reports, rejected=rejected)
    try:
        reports, rejected = l1.parse_file(path, mapping)
        return IngestResult(reports=reports, rejected=rejected)
    except Exception:  # noqa: BLE001
        log.warning("B1: L1 parse_file failed, falling back to L0", exc_info=True)
        reports, rejected = l0.parse_file(path, mapping)
        return IngestResult(reports=reports, rejected=rejected)


def normalize(raw: dict[str, object], mapping: dict[str, str]) -> Report:
    """Приведение сырой строки к Report. При USE_MOCK или ошибке L1 — тихий откат на L0."""
    if settings.USE_MOCK:
        return l0.normalize(raw, mapping)
    try:
        return l1.normalize(raw, mapping)
    except Exception:  # noqa: BLE001
        log.warning("B1: L1 normalize failed, falling back to L0", exc_info=True)
        return l0.normalize(raw, mapping)
