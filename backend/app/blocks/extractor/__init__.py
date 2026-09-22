"""Блок L1 · LLM: извлечение признаков и проверка на нейрослоп. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/L1_extractor.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from app.contracts.models import Extracted, Report, Verification


def extract(report: Report) -> Extracted:
    raise NotImplementedError(
        "L1: реализуй по контракту docs/contracts/L1_extractor.md"
    )


def verify(report: Report, nearby: list[Report]) -> Verification:
    raise NotImplementedError(
        "L1: реализуй по контракту docs/contracts/L1_extractor.md"
    )
