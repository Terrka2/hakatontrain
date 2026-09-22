"""Блок D1 · База данных и репозиторий. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/D1_db.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from app.contracts.models import Report


class Repository:
    """Интерфейс описан в контракте D1. Остальные блоки работают только через него."""

    def list_reports(
        self, *, status: str | None = None, category: str | None = None
    ) -> list[Report]:
        raise NotImplementedError("D1: реализуй по контракту docs/contracts/D1_db.md")


def get_repository() -> Repository:
    raise NotImplementedError("D1: реализуй по контракту docs/contracts/D1_db.md")
