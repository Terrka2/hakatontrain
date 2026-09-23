"""Блок L1 · LLM: извлечение признаков и проверка на нейрослоп. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/L1_extractor.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from app.contracts.models import Extracted, Report, Verification

from . import l0


def extract(report: Report) -> Extracted:
    return l0.extract(report)


def verify(report: Report, nearby: list[Report]) -> Verification:
    return l0.verify(report, nearby)
