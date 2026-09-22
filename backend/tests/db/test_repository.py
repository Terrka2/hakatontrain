"""Тесты репозитория D1 (уровень L0)."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.core.config import settings
from app.db import get_repository, l0

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "app"
    / "fixtures"
    / "demo_city.json"
)


@pytest.fixture
def fixture_data() -> dict[str, Any]:
    """Загрузка fixture demo_city.json."""
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_l0_reset_and_list_reports(fixture_data: dict[str, Any]) -> None:
    """Проверка reset() и фильтрации list_reports(status='open') для L0."""
    repo = get_repository()
    repo.reset()
    open_reports = repo.list_reports(status="open")
    expected_count = fixture_data["expect"]["open_reports"]
    assert len(open_reports) == expected_count


def test_l1_fallback_to_l0(monkeypatch: pytest.MonkeyPatch) -> None:
    """При USE_MOCK=False и ошибке L1 порт откатывается на l0.repo."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    repo = get_repository()
    assert repo is l0.repo
    assert len(repo.list_reports(status="open")) == 15
