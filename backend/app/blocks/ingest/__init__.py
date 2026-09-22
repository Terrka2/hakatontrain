"""Блок B1 · Парсер и импорт обращений. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B1_ingest.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from pathlib import Path

from pydantic import BaseModel

from app.contracts.models import Report


class IngestResult(BaseModel):
    reports: list[Report]
    rejected: list[dict[str, object]]  # {"row": int, "reason": str}


def load_fixture() -> list[Report]:
    raise NotImplementedError("B1: реализуй по контракту docs/contracts/B1_ingest.md")


def parse_file(path: Path, mapping: dict[str, str] | None = None) -> IngestResult:
    raise NotImplementedError("B1: реализуй по контракту docs/contracts/B1_ingest.md")


def normalize(raw: dict[str, object], mapping: dict[str, str]) -> Report:
    raise NotImplementedError("B1: реализуй по контракту docs/contracts/B1_ingest.md")
