"""Уровень L1 блока D1: SqlRepository на PostgreSQL/SQLModel (в разработке).

На этапе L0 модуль предоставляет заглушку repo, выбрасывающую NotImplementedError,
для проверки безопасного отката (fallback) порта на l0.repo при любых сбоях.
"""

from typing import Any


class SqlRepository:
    """Заглушка реализации SqlRepository (L1)."""

    def __init__(self) -> None:
        raise NotImplementedError("D1: L1 SqlRepository еще не реализован")


def __getattr__(name: str) -> Any:
    if name == "repo":
        raise NotImplementedError("D1: L1 SqlRepository еще не реализован")
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

