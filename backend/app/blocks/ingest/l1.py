"""L1: целевой уровень парсера и импорта обращений.

Любая ошибка L1 перехватывается в __init__.py с тихим откатом на l0.py.
"""

from pathlib import Path
from typing import Any

from app.contracts.models import Report

from . import l0


def load_fixture() -> list[Report]:
    """В L1 загрузка fixture совпадает с l0."""
    return l0.load_fixture()


def normalize(raw: dict[str, Any], mapping: dict[str, str]) -> Report:
    """Нормализация строки в Report."""
    return l0.normalize(raw, mapping)


def parse_file(
    path: Path, mapping: dict[str, str] | None = None
) -> tuple[list[Report], list[dict[str, Any]]]:
    """Парсинг файла с маппингом."""
    return l0.parse_file(path, mapping)
