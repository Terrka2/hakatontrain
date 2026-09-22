"""Тесты отдельных факторов блока B4 (priority).

Каждый фактор имеет свой файл и свой тест по контракту docs/contracts/B4_priority.md.
"""

from datetime import UTC, datetime

from app.blocks.priority import factors
from app.contracts.models import (
    Cluster,
    Context,
    Extracted,
    GeoPoint,
    Report,
)

NOW = datetime(2026, 9, 26, 7, 0, 0, tzinfo=UTC)
DUMMY_CTX = Context(now=NOW, weather=None, events=[], infrastructure=[])


def make_dummy_cluster(category: str, days_old: float = 1.0) -> Cluster:
    """Создаёт тестовый кластер с заданным возрастом."""
    ts = datetime.fromtimestamp(NOW.timestamp() - days_old * 86400, tz=UTC)
    return Cluster(
        id="c_test",
        category=category,
        centroid=GeoPoint(lat=47.01, lon=28.84),
        report_ids=["r_test"],
        first_reported_at=ts,
        last_reported_at=ts,
        status="open",
    )


def test_factor_hz_base_and_signals() -> None:
    """Фактор HZ: проверка базовой опасности категорий и надбавки за сигналы."""
    c_pothole = make_dummy_cluster("pothole")
    r_normal = Report(
        id="r1",
        category="pothole",
        text="Обычная яма на дороге",
        location=GeoPoint(lat=47.0, lon=28.0),
        created_at=NOW,
    )
    score, ev = factors.hz.evaluate(c_pothole, [r_normal], [], DUMMY_CTX)
    assert score == 0.5
    assert len(ev) == 1

    # Сигнал в тексте: "упал" -> +0.2 -> 0.7
    r_injured = Report(
        id="r2",
        category="pothole",
        text="Глубокая яма, человек упал и получил травму",
        location=GeoPoint(lat=47.0, lon=28.0),
        created_at=NOW,
    )
    score_inj, ev_inj = factors.hz.evaluate(c_pothole, [r_injured], [], DUMMY_CTX)
    assert score_inj == 0.7
    assert len(ev_inj) == 2

    # Сигнал через extracted.injured -> +0.2
    r_ext = Report(
        id="r3",
        category="pothole",
        text="Яма",
        extracted=Extracted(injured=True),
        location=GeoPoint(lat=47.0, lon=28.0),
        created_at=NOW,
    )
    score_ext, _ = factors.hz.evaluate(c_pothole, [r_ext], [], DUMMY_CTX)
    assert score_ext == 0.7

    # Категория manhole (база 0.9) с сигналом -> максимум 1.0
    c_manhole = make_dummy_cluster("manhole")
    score_manhole, _ = factors.hz.evaluate(c_manhole, [r_injured], [], DUMMY_CTX)
    assert score_manhole == 1.0


def test_factor_dm_demand_calculation() -> None:
    """Фактор DM: формула min(1, (кол-во обращений + confirmations) / 10)."""
    c = make_dummy_cluster("pothole")
    r1 = Report(
        id="r1",
        category="pothole",
        text="Яма 1",
        confirmations=3,
        location=GeoPoint(lat=47.0, lon=28.0),
        created_at=NOW,
    )
    r2 = Report(
        id="r2",
        category="pothole",
        text="Яма 2",
        confirmations=2,
        location=GeoPoint(lat=47.0, lon=28.0),
        created_at=NOW,
    )
    # (2 обращения + 5 подтверждений) / 10 = 0.7
    score, ev = factors.dm.evaluate(c, [r1, r2], [], DUMMY_CTX)
    assert score == 0.7
    assert len(ev) > 0

    # Переполнение: 15 подтверждений -> 1.0
    r3 = Report(
        id="r3",
        category="pothole",
        text="Яма 3",
        confirmations=15,
        location=GeoPoint(lat=47.0, lon=28.0),
        created_at=NOW,
    )
    score_max, _ = factors.dm.evaluate(c, [r3], [], DUMMY_CTX)
    assert score_max == 1.0


def test_factor_ag_age_calculation() -> None:
    """Фактор AG: формула min(1, дней с first_reported_at / 14)."""
    # 7 дней -> 7/14 = 0.5
    c_7d = make_dummy_cluster("pothole", days_old=7.0)
    score_7d, ev_7d = factors.ag.evaluate(c_7d, [], [], DUMMY_CTX)
    assert abs(score_7d - 0.5) < 1e-3
    assert len(ev_7d) > 0

    # 14 дней -> 1.0
    c_14d = make_dummy_cluster("pothole", days_old=14.0)
    score_14d, _ = factors.ag.evaluate(c_14d, [], [], DUMMY_CTX)
    assert score_14d == 1.0

    # 28 дней -> кап 1.0
    c_28d = make_dummy_cluster("pothole", days_old=28.0)
    score_28d, _ = factors.ag.evaluate(c_28d, [], [], DUMMY_CTX)
    assert score_28d == 1.0


def test_factor_sp_l0_returns_none() -> None:
    """Фактор SP: в L0 возвращает None."""
    c = make_dummy_cluster("pothole")
    score, ev = factors.sp.evaluate(c, [], [], DUMMY_CTX)
    assert score is None
    assert ev == []


def test_factor_rc_l0_returns_none() -> None:
    """Фактор RC: в L0 возвращает None."""
    c = make_dummy_cluster("pothole")
    score, ev = factors.rc.evaluate(c, [], [], DUMMY_CTX)
    assert score is None
    assert ev == []


def test_factor_ex_l0_returns_none() -> None:
    """Фактор EX: в ядре всегда возвращает None."""
    c = make_dummy_cluster("pothole")
    score, ev = factors.ex.evaluate(c, [], [], DUMMY_CTX)
    assert score is None
    assert ev == []


def test_factor_wx_l0_returns_none() -> None:
    """Фактор WX: в L0 возвращает None."""
    c = make_dummy_cluster("pothole")
    score, ev = factors.wx.evaluate(c, [], [], DUMMY_CTX)
    assert score is None
    assert ev == []


def test_factor_vf_l0_returns_none() -> None:
    """Фактор VF: в L0 возвращает None."""
    c = make_dummy_cluster("pothole")
    score, ev = factors.vf.evaluate(c, [], [], DUMMY_CTX)
    assert score is None
    assert ev == []
