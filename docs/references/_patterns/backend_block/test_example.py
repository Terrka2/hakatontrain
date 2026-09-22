"""Тесты блока <ID>. Один критерий приёмки = минимум один тест. Данные — только fixture, сеть запрещена.

Запуск: cd backend && uv run pytest tests/blocks/example -q
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.blocks.example import score
from app.contracts.models import Cluster, Context, Report

FIXTURE = Path(__file__).resolve().parents[3] / "app" / "fixtures" / "demo_city.json"


@pytest.fixture(scope="module")
def data() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def reports(data: dict) -> list[Report]:
    return [Report(**r) for r in data["reports"]]


def _cluster_of(report: Report) -> Cluster:
    return Cluster(
        id=report.id, category=report.category, centroid=report.location, report_ids=[report.id],
        first_reported_at=report.created_at, last_reported_at=report.created_at,
    )


def test_manhole_scores_at_least_expected(data: dict, reports: list[Report]) -> None:
    """Критерий приёмки 1: люк набирает не меньше expect.min_score_manhole."""
    manhole = next(r for r in reports if r.category == "manhole")
    result = score(_cluster_of(manhole), [manhole], Context(now=datetime.now(UTC)))
    assert result.score >= data["expect"]["min_score_manhole"]


def test_is_deterministic(reports: list[Report]) -> None:
    """Два вызова на одних данных дают одинаковый результат."""
    r = reports[0]
    ctx = Context(now=datetime(2026, 9, 27, 9, 0, tzinfo=UTC))
    assert score(_cluster_of(r), [r], ctx) == score(_cluster_of(r), [r], ctx)


def test_l1_failure_falls_back_to_l0(monkeypatch: pytest.MonkeyPatch, reports: list[Report]) -> None:
    """Ошибка L1 не выходит наружу: порт откатывается на L0."""
    from app.blocks import example
    from app.core.config import settings

    monkeypatch.setattr(settings, "USE_MOCK", False)
    monkeypatch.setattr(example.l1, "score", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    r = reports[0]
    assert score(_cluster_of(r), [r], Context(now=datetime.now(UTC))).cluster_id == r.id
