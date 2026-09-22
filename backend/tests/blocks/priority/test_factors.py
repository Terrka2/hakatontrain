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
    InfraObject,
    Report,
    Verification,
    Weather,
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

    # Сигнал в структуре extracted -> +0.2
    r_struct = Report(
        id="r3",
        category="pothole",
        text="Яма",
        location=GeoPoint(lat=47.0, lon=28.0),
        created_at=NOW,
        extracted=Extracted(injured=True),
    )
    score_str, _ = factors.hz.evaluate(c_pothole, [r_struct], [], DUMMY_CTX)
    assert score_str == 0.7

    # Категория manhole (0.9) + сигнал -> кап 1.0
    c_manhole = make_dummy_cluster("manhole")
    score_cap, _ = factors.hz.evaluate(c_manhole, [r_injured], [], DUMMY_CTX)
    assert score_cap == 1.0


def test_factor_dm_demand_calculation() -> None:
    """Фактор DM: формула min(1, (reports + confirmations) / 10)."""
    c = make_dummy_cluster("pothole")
    # 1 report, 0 confirmations -> 1/10 = 0.1
    r1 = Report(
        id="r1",
        category="pothole",
        text="Яма",
        location=GeoPoint(lat=47.0, lon=28.0),
        confirmations=0,
        created_at=NOW,
    )
    score1, ev1 = factors.dm.evaluate(c, [r1], [], DUMMY_CTX)
    assert score1 == 0.1
    assert len(ev1) > 0

    # 2 reports, 3 confirmations -> (2 + 3) / 10 = 0.5
    r2 = Report(
        id="r2",
        category="pothole",
        text="Яма 2",
        location=GeoPoint(lat=47.0, lon=28.0),
        confirmations=3,
        created_at=NOW,
    )
    score2, _ = factors.dm.evaluate(c, [r1, r2], [], DUMMY_CTX)
    assert score2 == 0.5

    # 1 report, 9 confirmations -> (1 + 9) / 10 = 1.0
    r3 = Report(
        id="r3",
        category="pothole",
        text="Яма 3",
        location=GeoPoint(lat=47.0, lon=28.0),
        confirmations=9,
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


def test_factor_sp_social_objects() -> None:
    """Фактор SP: проверка расстояния до школ/детсадов/больниц."""
    c = make_dummy_cluster("pothole")
    # 1. Нет инфраструктуры -> None
    score_none, ev_none = factors.sp.evaluate(c, [], [], DUMMY_CTX)
    assert score_none is None
    assert ev_none == []

    # 2. Объект рядом (100 м) -> 1.0
    # 0.0009 градуса широты ≈ 100 метров
    ctx_near = Context(
        now=NOW,
        weather=None,
        events=[],
        infrastructure=[
            InfraObject(
                id="s1",
                kind="school",
                name="Школа №1",
                location=GeoPoint(lat=47.0109, lon=28.84),
            )
        ],
    )
    score_near, ev_near = factors.sp.evaluate(c, [], [], ctx_near)
    assert score_near == 1.0
    assert len(ev_near) > 0

    # 3. Объект на среднем расстоянии (250 м) -> 0.5
    # 0.0022 градуса широты ≈ 245 метров
    ctx_mid = Context(
        now=NOW,
        weather=None,
        events=[],
        infrastructure=[
            InfraObject(
                id="k1",
                kind="kindergarten",
                name="Детсад №5",
                location=GeoPoint(lat=47.0122, lon=28.84),
            )
        ],
    )
    score_mid, ev_mid = factors.sp.evaluate(c, [], [], ctx_mid)
    assert score_mid == 0.5
    assert len(ev_mid) > 0

    # 4. Объект далеко (500 м) -> 0.0
    ctx_far = Context(
        now=NOW,
        weather=None,
        events=[],
        infrastructure=[
            InfraObject(
                id="h1",
                kind="hospital",
                name="Больница",
                location=GeoPoint(lat=47.015, lon=28.84),
            )
        ],
    )
    score_far, _ = factors.sp.evaluate(c, [], [], ctx_far)
    assert score_far == 0.0

    # 5. Только остановка (stop) -> не соц. объект -> 0.0
    ctx_stop = Context(
        now=NOW,
        weather=None,
        events=[],
        infrastructure=[
            InfraObject(
                id="st1",
                kind="stop",
                name="Остановка",
                location=GeoPoint(lat=47.0101, lon=28.84),
            )
        ],
    )
    score_stop, _ = factors.sp.evaluate(c, [], [], ctx_stop)
    assert score_stop == 0.0


def test_factor_rc_recurrence() -> None:
    """Фактор RC: повтор проблемы в радиусе 60 м за 12 месяцев."""
    c = make_dummy_cluster("pothole")
    # 1. Пустая история -> None
    score_none, ev_none = factors.rc.evaluate(c, [], [], DUMMY_CTX)
    assert score_none is None
    assert ev_none == []

    # 2. Решённое обращение той же категории в 20 м (3 месяца назад) -> 1.0
    # 0.0002 градуса широты ≈ 22 метра
    h_match = Report(
        id="h001",
        category="pothole",
        text="Старая яма",
        location=GeoPoint(lat=47.0102, lon=28.84),
        created_at=datetime.fromtimestamp(NOW.timestamp() - 90 * 86400, tz=UTC),
        status="resolved",
    )
    score_match, ev_match = factors.rc.evaluate(c, [], [h_match], DUMMY_CTX)
    assert score_match == 1.0
    assert "h001" in ev_match[0]

    # 3. Другая категория -> 0.0
    h_other_cat = h_match.model_copy(update={"category": "streetlight"})
    score_diff_cat, _ = factors.rc.evaluate(c, [], [h_other_cat], DUMMY_CTX)
    assert score_diff_cat == 0.0

    # 4. Не resolved (напр. open) -> 0.0
    h_open = h_match.model_copy(update={"status": "open"})
    score_open, _ = factors.rc.evaluate(c, [], [h_open], DUMMY_CTX)
    assert score_open == 0.0

    # 5. Старше 12 месяцев (напр. 400 дней) -> 0.0
    h_old = h_match.model_copy(
        update={
            "created_at": datetime.fromtimestamp(NOW.timestamp() - 400 * 86400, tz=UTC)
        }
    )
    score_old, _ = factors.rc.evaluate(c, [], [h_old], DUMMY_CTX)
    assert score_old == 0.0

    # 6. Дальше 60 м (напр. 150 м) -> 0.0
    h_far = h_match.model_copy(update={"location": GeoPoint(lat=47.0115, lon=28.84)})
    score_far, _ = factors.rc.evaluate(c, [], [h_far], DUMMY_CTX)
    assert score_far == 0.0


def test_factor_ex_stub() -> None:
    """Фактор EX: всегда заглушка None (реализуется X1)."""
    c = make_dummy_cluster("pothole")
    score, ev = factors.ex.evaluate(c, [], [], DUMMY_CTX)
    assert score is None
    assert ev == []


def test_factor_wx_weather() -> None:
    """Фактор WX: погодные условия (ветер для tree, мороз для water_leak)."""
    c_tree = make_dummy_cluster("tree")
    c_water = make_dummy_cluster("water_leak")
    c_pothole = make_dummy_cluster("pothole")

    # 1. Погода None -> None
    score_none, ev_none = factors.wx.evaluate(c_tree, [], [], DUMMY_CTX)
    assert score_none is None
    assert ev_none == []

    # 2. Штормовой ветер (16 м/с) -> для tree 1.0, для других 0.0
    ctx_storm = Context(
        now=NOW,
        weather=Weather(
            at=NOW,
            precipitation_mm=5.0,
            wind_ms=16.0,
            temp_c=12.0,
            source="test",
        ),
        events=[],
        infrastructure=[],
    )
    score_tree_storm, ev_tree = factors.wx.evaluate(c_tree, [], [], ctx_storm)
    assert score_tree_storm == 1.0
    assert len(ev_tree) > 0

    score_pothole_storm, _ = factors.wx.evaluate(c_pothole, [], [], ctx_storm)
    assert score_pothole_storm == 0.0

    # 3. Мороз (-3°C) -> для water_leak 1.0, для других 0.0
    ctx_frost = Context(
        now=NOW,
        weather=Weather(
            at=NOW,
            precipitation_mm=0.0,
            wind_ms=2.0,
            temp_c=-3.0,
            source="test",
        ),
        events=[],
        infrastructure=[],
    )
    score_water_frost, ev_water = factors.wx.evaluate(c_water, [], [], ctx_frost)
    assert score_water_frost == 1.0
    assert len(ev_water) > 0

    # 4. Обычная погода -> 0.0
    ctx_normal = Context(
        now=NOW,
        weather=Weather(
            at=NOW,
            precipitation_mm=0.0,
            wind_ms=5.0,
            temp_c=18.0,
            source="test",
        ),
        events=[],
        infrastructure=[],
    )
    score_normal, _ = factors.wx.evaluate(c_water, [], [], ctx_normal)
    assert score_normal == 0.0


def test_factor_vf_verification() -> None:
    """Фактор VF: достоверность по наличию фото или plausible/confirmed."""
    c = make_dummy_cluster("pothole")
    # 1. Пустой список отчётов -> 0.0
    score_empty, ev_empty = factors.vf.evaluate(c, [], [], DUMMY_CTX)
    assert score_empty == 0.0
    assert ev_empty == []

    # 2. Обращение с фото -> 1.0
    r_photo = Report(
        id="r1",
        category="pothole",
        text="Яма",
        location=GeoPoint(lat=47.0, lon=28.0),
        photo_url="http://example.com/p.jpg",
        created_at=NOW,
    )
    score_photo, ev_photo = factors.vf.evaluate(c, [r_photo], [], DUMMY_CTX)
    assert score_photo == 1.0
    assert len(ev_photo) > 0

    # 3. Обращение со статусом confirmed -> 1.0
    r_conf = Report(
        id="r2",
        category="pothole",
        text="Яма",
        location=GeoPoint(lat=47.0, lon=28.0),
        created_at=NOW,
        verification=Verification(status="confirmed"),
    )
    score_conf, _ = factors.vf.evaluate(c, [r_conf], [], DUMMY_CTX)
    assert score_conf == 1.0

    # 4. Неверифицированное обращение без фото -> 0.0
    r_unver = Report(
        id="r3",
        category="pothole",
        text="Яма",
        location=GeoPoint(lat=47.0, lon=28.0),
        created_at=NOW,
    )
    score_unver, _ = factors.vf.evaluate(c, [r_unver], [], DUMMY_CTX)
    assert score_unver == 0.0

    # 5. 2 из 4 верифицированы -> 0.5
    score_half, _ = factors.vf.evaluate(
        c, [r_photo, r_conf, r_unver, r_unver], [], DUMMY_CTX
    )
    assert score_half == 0.5
