"""Уровень L1 блока D1: SqlRepository на PostgreSQL/SQLModel (в разработке).

Заглушка: любой вызов метода кидает NotImplementedError, чтобы порт в __init__.py
мог перехватить исключение и безопасно откатиться на L0.
"""

from typing import Any


class SqlRepository:
    """Заглушка реализации SqlRepository (L1): любой вызов метода кидает NotImplementedError."""

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("__") and name.endswith("__"):
            return super().__getattribute__(name)
        raise NotImplementedError(f"D1: L1 SqlRepository.{name} еще не реализован")

    def __getattr__(self, name: str) -> Any:
        raise NotImplementedError(f"D1: L1 SqlRepository.{name} еще не реализован")


def __getattr__(name: str) -> Any:
    if name == "repo":
        raise NotImplementedError("D1: L1 SqlRepository еще не реализован")
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
