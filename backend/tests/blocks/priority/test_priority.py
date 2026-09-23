"""Тесты блока B4 (объяснимый приоритет).

Критерии приёмки B4:
1. r011 (люк у детсада) -> score >= expect.min_score_manhole (80) и есть фактор FL; r001 -> score >= expect.min_score_school_pothole (70).
2. r011 и r001 — первые два по баллу среди всех кластеров.
3. r005 -> score <= expect.max_score_low_noise (30).
4. Сумма points всех факторов = score +- 0.1.
5. При ctx.weather=None и пустой инфраструктуре балл считается, WX и SP имеют score=None, confidence < 1.
6. Кластер r006 (suspicious) -> needs_review=True.
7. При пустом ctx.events фактор EX имеет score=None и балл не ломается.
8. У каждого фактора с score > 0 непустой evidence на русском.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from app.blocks import priority
from app.contracts.models import (
    Cluster,
    Context,
    GeoPoint,
    Report,
    Verification,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "app" / "fixtures" / "demo_city.json"
)


@pytest.fixture(autouse=True)
def disable_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Запрещает любые сетевые вызовы в тестах блока."""

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("Network access forbidden in block tests")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("socket.socket.connect", forbidden)


@pytest.fixture
def fixture_data() -> dict[str, Any]:
    """Загрузка демо-города demo_city.json."""
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def reports_map(fixture_data: dict[str, Any]) -> dict[str, Report]:
    """Словарь всех обращений из demo_city.json."""
    return {r["id"]: Report(**r) for r in fixture_data["reports"]}


@pytest.fixture
def base_context(fixture_data: dict[str, Any]) -> Context:
    """Базовый контекст из demo_city.json."""
    return Context(
        now=datetime.fromisoformat(fixture_data["now"]),
        weather=None,
        events=[],
        infrastructure=[],
    )


def make_cluster(
    cluster_id: str,
    rep_list: list[Report],
) -> Cluster:
    """Создаёт Cluster на базе списка обращений."""
    first = min(rep_list, key=lambda r: r.created_at)
    last = max(rep_list, key=lambda r: r.created_at)
    return Cluster(
        id=cluster_id,
        category=first.category,
        centroid=first.location,
        report_ids=[r.id for r in rep_list],
        first_reported_at=first.created_at,
        last_reported_at=last.created_at,
        status="open",
    )


# ==============================================================================
# 1. Критерии приёмки
# ==============================================================================


def test_criterion_1_manhole_and_school_pothole_scores(
    reports_map: dict[str, Report],
    base_context: Context,
    fixture_data: dict[str, Any],
) -> None:
    """Критерий 1: r011 score >= min_score_manhole (80) + фактор FL; r001 score >= min_score_school_pothole (70)."""
    expect = fixture_data["expect"]

    # Кластер r011 (люк у детсада)
    c_r011 = make_cluster("c_r011", [reports_map["r011"]])
    res_r011 = priority.score(c_r011, [reports_map["r011"]], [], base_context)

    assert res_r011.score >= expect["min_score_manhole"], (
        f"Expected r011 score >= {expect['min_score_manhole']}, got {res_r011.score}"
    )
    fl_codes = [f.code for f in res_r011.factors if f.code == "FL"]
    assert len(fl_codes) == 1, "Expected FL factor in r011 priority"
    fl_factor = next(f for f in res_r011.factors if f.code == "FL")
    assert fl_factor.points > 0, "FL points should be positive"

    # Кластер r001 (яма у школы: r001, r002, r003)
    c_r001 = make_cluster(
        "c_r001",
        [reports_map["r001"], reports_map["r002"], reports_map["r003"]],
    )
    res_r001 = priority.score(
        c_r001,
        [reports_map["r001"], reports_map["r002"], reports_map["r003"]],
        [],
        base_context,
    )
    assert res_r001.score >= expect["min_score_school_pothole"], (
        f"Expected r001 score >= {expect['min_score_school_pothole']}, got {res_r001.score}"
    )


def test_criterion_2_top2_priority_clusters(
    reports_map: dict[str, Report],
    base_context: Context,
    fixture_data: dict[str, Any],
) -> None:
    """Критерий 2: r011 и r001 — первые два по приоритету среди всех кластеров города."""
    # Собираем все кластеры города: трио (r001, r002, r003) + остальные одиночные
    clusters: list[tuple[str, Cluster, list[Report]]] = []

    trio = [reports_map["r001"], reports_map["r002"], reports_map["r003"]]
    clusters.append(("r001", make_cluster("c_r001", trio), trio))

    for r_id, r in reports_map.items():
        if r_id in ("r001", "r002", "r003", "r016"):
            continue
        clusters.append((r_id, make_cluster(f"c_{r_id}", [r]), [r]))

    scores: list[tuple[str, float]] = []
    for lead_id, cluster, reps in clusters:
        p = priority.score(cluster, reps, [], base_context)
        scores.append((lead_id, p.score))

    scores.sort(key=lambda x: x[1], reverse=True)
    top2_ids = [s[0] for s in scores[:2]]

    assert set(top2_ids) == set(fixture_data["expect"]["top2_priority_reports"]), (
        f"Top 2 expected {fixture_data['expect']['top2_priority_reports']}, got {top2_ids}"
    )


def test_criterion_3_low_noise_report(
    reports_map: dict[str, Report],
    base_context: Context,
    fixture_data: dict[str, Any],
) -> None:
    """Критерий 3: кластер r005 получает score <= expect.max_score_low_noise (30)."""
    c_r005 = make_cluster("c_r005", [reports_map["r005"]])
    res = priority.score(c_r005, [reports_map["r005"]], [], base_context)
    max_noise = fixture_data["expect"]["max_score_low_noise"]
    assert res.score <= max_noise, f"Expected <= {max_noise}, got {res.score}"


def test_criterion_4_sum_points_equals_score(
    reports_map: dict[str, Report],
    base_context: Context,
) -> None:
    """Критерий 4: сумма points всех факторов = score +- 0.1."""
    for rep in reports_map.values():
        c = make_cluster(f"c_{rep.id}", [rep])
        p = priority.score(c, [rep], [], base_context)
        sum_pts = sum(f.points for f in p.factors)
        assert abs(sum_pts - p.score) <= 0.1, (
            f"Cluster {c.id}: sum(points)={sum_pts} != score={p.score}"
        )


def test_criterion_5_no_weather_and_empty_infra(
    reports_map: dict[str, Report],
    base_context: Context,
) -> None:
    """Критерий 5: при weather=None и infra=[] балл считается, WX и SP имеют score=None, confidence < 1."""
    c = make_cluster("c_r001", [reports_map["r001"]])
    p = priority.score(c, [reports_map["r001"]], [], base_context)

    factors_dict = {f.code: f for f in p.factors}
    assert factors_dict["WX"].score is None
    assert factors_dict["SP"].score is None
    assert p.confidence < 1.0
    assert p.score > 0


def test_criterion_6_suspicious_report_needs_review(
    reports_map: dict[str, Report],
    base_context: Context,
) -> None:
    """Критерий 6: кластер с обращением verification.status='suspicious' получает needs_review=True."""
    r = reports_map["r006"].model_copy(deep=True)
    r.verification = Verification(
        status="suspicious", reasons=["AI anomaly"], confidence=0.9
    )

    c = make_cluster("c_r006", [r])
    p = priority.score(c, [r], [], base_context)
    assert p.needs_review is True


def test_criterion_8_empty_events_ex_none(
    reports_map: dict[str, Report],
    base_context: Context,
) -> None:
    """Критерий 8: при пустом ctx.events фактор EX имеет score=None и балл не ломается."""
    c = make_cluster("c_r001", [reports_map["r001"]])
    p = priority.score(c, [reports_map["r001"]], [], base_context)
    ex_factor = next(f for f in p.factors if f.code == "EX")
    assert ex_factor.score is None
    assert ex_factor.evidence == []


def test_criterion_9_nonempty_evidence_on_russian(
    reports_map: dict[str, Report],
    base_context: Context,
) -> None:
    """Критерий 9: у каждого фактора с score > 0 непустой evidence на русском."""
    c = make_cluster("c_r001", [reports_map["r001"]])
    p = priority.score(c, [reports_map["r001"]], [], base_context)

    for f in p.factors:
        if f.score is not None and f.score > 0:
            assert len(f.evidence) > 0, (
                f"Factor {f.code} has positive score but empty evidence"
            )
            assert any(
                any("\u0400" <= ch <= "\u04ff" for ch in line) for line in f.evidence
            ), f"Factor {f.code} evidence must be in Russian"


# ==============================================================================
# 2. QA Чеклист: границы данных, детерминированность, веса
# ==============================================================================


def test_qa_data_boundaries(base_context: Context) -> None:
    """QA 3: Границы данных: пустой список reports, 0 confirmations, далёкие даты."""
    # Пустой список обращений
    c_empty = Cluster(
        id="c_empty",
        category="pothole",
        centroid=GeoPoint(lat=47.0, lon=28.0),
        report_ids=[],
        first_reported_at=base_context.now,
        last_reported_at=base_context.now,
    )
    p_empty = priority.score(c_empty, [], [], base_context)
    assert p_empty.score >= 0.0
    assert len(p_empty.factors) >= 8

    # Дата в будущем (разница отрицательная -> возраст 0)
    c_future = Cluster(
        id="c_future",
        category="pothole",
        centroid=GeoPoint(lat=47.0, lon=28.0),
        report_ids=[],
        first_reported_at=datetime(2030, 1, 1, tzinfo=base_context.now.tzinfo),
        last_reported_at=datetime(2030, 1, 1, tzinfo=base_context.now.tzinfo),
    )
    p_future = priority.score(c_future, [], [], base_context)
    ag_factor = next(f for f in p_future.factors if f.code == "AG")
    assert ag_factor.score == 0.0


def test_qa_determinism(reports_map: dict[str, Report], base_context: Context) -> None:
    """QA 5: Детерминированность: два вызова подряд дают идентичный результат."""
    c = make_cluster("c_r001", [reports_map["r001"]])
    res1 = priority.score(c, [reports_map["r001"]], [], base_context)
    res2 = priority.score(c, [reports_map["r001"]], [], base_context)
    assert res1.model_dump() == res2.model_dump()


def test_qa_custom_weights(
    reports_map: dict[str, Report], base_context: Context
) -> None:
    """Проверка кастомных весов: переопределение веса меняет итоговый результат."""
    c = make_cluster("c_r001", [reports_map["r001"]])
    res_default = priority.score(c, [reports_map["r001"]], [], base_context)

    # Увеличиваем вес AG до 1.0, обнуляем HZ и DM
    res_custom = priority.score(
        c,
        [reports_map["r001"]],
        [],
        base_context,
        weights={"HZ": 0.0, "DM": 0.0, "AG": 1.0},
    )
    assert res_default.score != res_custom.score
