"""Тесты репозитория D1 (L0 MemoryRepository и L1 SqlRepository)."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.db import Repository, get_repository
from app.db.l0 import MemoryRepository


@pytest.fixture
def fixture_data() -> dict[str, Any]:
    """Загрузка fixture demo_city.json."""
    fixture_path = (
        Path(__file__).resolve().parent.parent.parent
        / "app"
        / "fixtures"
        / "demo_city.json"
    )
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize(
    "repo_factory",
    [
        pytest.param(lambda: get_repository(), id="get_repository_l0"),
        pytest.param(lambda: MemoryRepository(), id="memory_repository_direct"),
    ],
)
def test_l0_reset_and_list_reports(
    fixture_data: dict[str, Any], repo_factory: Callable[[], Repository]
) -> None:
    """Проверка reset() и фильтрации list_reports(status='open') по demo_city.json."""
    repo = repo_factory()
    repo.reset()
    open_reports = repo.list_reports(status="open")
    expected_count = fixture_data["expect"]["open_reports"]
    assert len(open_reports) == expected_count
