"""Тесты репозитория D1 (уровень L0)."""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from app.contracts.models import (
    Cluster,
    CrewRoute,
    Event,
    Extracted,
    GeoPoint,
    OperatorRun,
    Plan,
    Priority,
    Report,
    Verification,
)
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
    """Проверка reset() и фильтрации list_reports(status='open') по demo_city.json."""
    repo = get_repository()
    repo.reset()
    open_reports = repo.list_reports(status="open")
    expected_count = fixture_data["expect"]["open_reports"]
    assert len(open_reports) == expected_count


def test_reset_restores_exact_fixture_state(fixture_data: dict[str, Any]) -> None:
    """Критерий 2: reset() восстанавливает полное точное состояние fixture demo_city.json."""
    repo = get_repository()
    # Мутируем состояние, подтверждая репорт и сбрасывая
    repo.confirm_report("r001")
    repo.reset()

    # 1. Проверка reports по id и ключевым полям
    reports = repo.list_reports()
    expected_reports = {r["id"]: r for r in fixture_data["reports"]}
    assert len(reports) == len(expected_reports)
    for r in reports:
        exp = expected_reports[r.id]
        assert r.category == exp["category"]
        assert r.status == exp["status"]
        assert r.text == exp["text"]
        assert r.confirmations == exp["confirmations"]
        assert r.location.lat == exp["location"]["lat"]
        assert r.location.lon == exp["location"]["lon"]

    # 2. Проверка infrastructure
    infra = repo.list_infrastructure()
    expected_infra = {i["id"]: i for i in fixture_data["infrastructure"]}
    assert len(infra) == len(expected_infra)
    for i in infra:
        exp_i = expected_infra[i.id]
        assert i.kind == exp_i["kind"]
        assert i.name == exp_i["name"]
        assert i.location.lat == exp_i["location"]["lat"]
        assert i.location.lon == exp_i["location"]["lon"]

    # 3. Проверка crews
    crews = repo.list_crews()
    expected_crews = {c["id"]: c for c in fixture_data["crews"]}
    assert len(crews) == len(expected_crews)
    for c in crews:
        exp_c = expected_crews[c.id]
        assert c.name == exp_c["name"]
        assert c.skills == exp_c["skills"]
        assert c.start.lat == exp_c["start"]["lat"]
        assert c.start.lon == exp_c["start"]["lon"]


def test_upsert_reports_no_duplicates(fixture_data: dict[str, Any]) -> None:
    """Критерий 3: upsert_reports дважды с теми же данными не создает дубликатов."""
    repo = get_repository()
    repo.reset()
    initial_reports = repo.list_reports()
    initial_count = len(initial_reports)
    assert (
        len(repo.list_reports(status="open")) == fixture_data["expect"]["open_reports"]
    )

    now_dt = datetime(2026, 9, 26, 8, 0, tzinfo=UTC)
    new_reports = [
        Report(
            id=f"new_r{i}",
            category="pothole",
            text=f"New test pothole {i}",
            location=GeoPoint(lat=47.01 + i * 0.001, lon=28.84),
            created_at=now_dt,
            status="open",
        )
        for i in range(3)
    ]

    # Первый импорт 3 отчетов
    res1 = repo.upsert_reports(new_reports)
    assert res1 == 3
    assert len(repo.list_reports()) == initial_count + 3

    # Повторный импорт тех же 3 отчетов
    res2 = repo.upsert_reports(new_reports)
    assert res2 == 3
    # Количество в базе должно увеличиться ровно на 3 (не на 6)
    assert len(repo.list_reports()) == initial_count + 3


def test_l1_fallback_to_l0(
    fixture_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """При USE_MOCK=False и ошибке L1 порт откатывается на l0.repo."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    repo = get_repository()
    assert repo is l0.repo
    repo.reset()
    assert (
        len(repo.list_reports(status="open")) == fixture_data["expect"]["open_reports"]
    )


def test_list_events_window_covering_and_naive_datetime() -> None:
    """Баги 1 и 2: list_events находит события, накрывающие окно, и поддерживает naive datetime."""
    repo = get_repository()
    repo.reset()

    event = Event(
        id="wide_event",
        title="Длинный фестиваль",
        location=GeoPoint(lat=47.02, lon=28.83),
        starts_at=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 30, 20, 0, tzinfo=UTC),
    )
    repo.add_event(event)

    # Окно поиска целиком внутри события, наивные даты
    search_start = datetime(2026, 9, 24, 12, 0)
    search_end = datetime(2026, 9, 25, 12, 0)

    matching = repo.list_events(search_start, search_end)
    matching_ids = [e.id for e in matching]
    assert "wide_event" in matching_ids


def test_current_plan_returns_highest_version() -> None:
    """Баг 3: current_plan возвращает план с максимальной версией."""
    repo = get_repository()
    repo.reset()

    today = date(2026, 9, 26)
    plan_v1 = Plan(
        id="p_v1",
        day=today,
        routes=[CrewRoute(crew_id="c1", stops=[])],
        status="approved",
        version=1,
    )
    plan_v2 = Plan(
        id="p_v2",
        day=today,
        routes=[CrewRoute(crew_id="c1", stops=[])],
        status="approved",
        version=2,
    )

    repo.save_plan(plan_v1)
    repo.save_plan(plan_v2)

    active = repo.current_plan(status="approved")
    assert active is not None
    assert active.id == "p_v2"
    assert active.version == 2


def test_list_runs_limit() -> None:
    """Баг 4: list_runs(limit=0) возвращает пустой список, limit>0 возвращает последние N."""
    repo = get_repository()
    repo.reset()

    for i in range(5):
        run = OperatorRun(
            id=f"run_{i}",
            trigger="manual",
            at=datetime(2026, 9, 26, 10, i, tzinfo=UTC),
            reports_seen=i,
            clusters_total=i,
            clusters_new=0,
        )
        repo.add_run(run)

    assert repo.list_runs(limit=0) == []
    runs_2 = repo.list_runs(limit=2)
    assert len(runs_2) == 2
    assert runs_2[0].id == "run_4"
    assert runs_2[1].id == "run_3"


def test_upsert_preserves_enrichment() -> None:
    """Проблема 1: upsert_reports сохраняет cluster_id, extracted и verification."""
    repo = get_repository()
    repo.reset()

    # Обогащаем отчет r001
    r001 = repo.list_reports(status="open")[0]
    enriched = r001.model_copy(
        update={
            "cluster_id": "cluster_99",
            "extracted": Extracted(hazard_signals=["яма"]),
            "verification": Verification(status="confirmed", confidence=0.9),
        }
    )
    repo.upsert_reports([enriched])

    # Сырой отчет без обогащения
    raw = r001.model_copy(
        update={
            "cluster_id": None,
            "extracted": None,
            "verification": None,
            "confirmations": 10,
        }
    )
    repo.upsert_reports([raw])

    updated = [r for r in repo.list_reports() if r.id == r001.id][0]
    assert updated.cluster_id == "cluster_99"
    assert updated.extracted is not None
    assert updated.extracted.hazard_signals == ["яма"]
    assert updated.verification is not None
    assert updated.verification.status == "confirmed"
    assert updated.confirmations == 10


def test_immutability_deep_copy() -> None:
    """Проблема 2: репозиторий защищен от мутаций извне."""
    repo = get_repository()
    repo.reset()

    first = repo.list_reports()[0]
    first.text = "MUTATED_OUTSIDE"

    fresh = repo.list_reports()[0]
    assert fresh.text != "MUTATED_OUTSIDE"


def test_set_needs_review_validation_and_reason() -> None:
    """Проблема 3: set_needs_review валидирует cluster_id и сохраняет reason."""
    repo = get_repository()
    repo.reset()

    # Несуществующий кластер -> ValueError
    with pytest.raises(ValueError, match="does not exist"):
        repo.set_needs_review("non_existent_cluster", True, "some reason")

    # Существующий кластер
    c = Cluster(
        id="c_test",
        category="pothole",
        centroid=GeoPoint(lat=47.01, lon=28.84),
        report_ids=["r001"],
        first_reported_at=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
        last_reported_at=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
    )
    p = Priority(
        cluster_id="c_test",
        score=75.0,
        factors=[],
        confidence=1.0,
        needs_review=False,
    )
    repo.save_clusters([c], {"c_test": p})

    repo.set_needs_review("c_test", True, "Hazardous near school")
    assert repo._needs_review_reasons.get("c_test") == "Hazardous near school"
    cluster_pairs = repo.list_clusters()
    matching = [
        priority for cluster, priority in cluster_pairs if cluster.id == "c_test"
    ]
    assert len(matching) == 1
    assert matching[0] is not None
    assert matching[0].needs_review is True
