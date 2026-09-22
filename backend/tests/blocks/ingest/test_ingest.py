"""Тесты блока B1 (ingest).

Один критерий приёмки = минимум один тест.
Все тесты проходят БЕЗ сети и БЕЗ базы данных.
"""

import json
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.blocks import ingest
from app.blocks.ingest.l0 import FIXTURE_PATH, reset_store
from app.core.config import settings
from app.main import app
from app.models import User


@pytest.fixture(autouse=True)
def clean_environment() -> Generator[None]:
    """Сбрасывает in-memory хранилище обращений до и после каждого теста."""
    reset_store()
    yield
    reset_store()


@pytest.fixture(autouse=True)
def disable_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Запрещает любые сетевые вызовы в тестах блока."""

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("Network access forbidden in block tests")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)


@pytest.fixture
def client() -> Generator[TestClient]:
    """TestClient для FastAPI приложения."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def fixture_data() -> dict[str, Any]:
    """Данные demo_city.json."""
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# ==============================================================================
# 1. Критерии приёмки
# ==============================================================================


def test_criterion_1_load_fixture_reports_and_open_count(
    fixture_data: dict[str, Any],
) -> None:
    """Критерий 1: load_fixture() возвращает 16 Report, из них expect.open_reports открытых."""
    reports = ingest.load_fixture()
    assert len(reports) == 16
    open_reports = [r for r in reports if r.status == "open"]
    expected_open = fixture_data["expect"]["open_reports"]
    assert len(open_reports) == expected_open


def test_criterion_2_csv_with_mapping_parses_without_code_change(
    tmp_path: Path,
) -> None:
    """Критерий 2: CSV с колонками на румынском/русском парсится через mapping без правки кода."""
    csv_content = (
        "identificator,categorie,descriere,latitudine,longitudine,adresa\n"
        "custom_01,pothole,Groapa mare pe carosabil,47.025,28.835,bd. Stefan cel Mare\n"
        "custom_02, streetlight, Nu functioneaza felinarul, 47.026, 28.836, str. Puskin\n"
    )
    csv_file = tmp_path / "reports_ro.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    mapping = {
        "identificator": "id",
        "categorie": "category",
        "descriere": "text",
        "latitudine": "lat",
        "longitudine": "lon",
        "adresa": "address",
    }

    result = ingest.parse_file(csv_file, mapping=mapping)
    assert len(result.rejected) == 0
    assert len(result.reports) == 2

    r1 = result.reports[0]
    assert r1.id == "custom_01"
    assert r1.category == "pothole"
    assert r1.text == "Groapa mare pe carosabil"
    assert r1.location.lat == 47.025
    assert r1.location.lon == 28.835
    assert r1.address == "bd. Stefan cel Mare"

    r2 = result.reports[1]
    assert r2.id == "custom_02"
    assert r2.category == "streetlight"
    assert r2.text == "Nu functioneaza felinarul"


def test_criterion_3_missing_coords_and_unknown_category_rejected(
    tmp_path: Path,
) -> None:
    """Критерий 3: Строка без координат и строка с неизвестной категорией попадают в rejected с причиной, импорт не падает."""
    csv_content = (
        "id,category,text,lat,lon\n"
        "valid_01,pothole,Нормальная яма,47.01,28.84\n"
        "no_coords,pothole,Яма без координат,,\n"
        "bad_cat,unknown_alien_category,НЛО приземлилось,47.02,28.85\n"
        "valid_02,garbage,Переполненные баки,47.03,28.86\n"
    )
    csv_file = tmp_path / "mixed.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    result = ingest.parse_file(csv_file)
    assert len(result.reports) == 2
    assert [r.id for r in result.reports] == ["valid_01", "valid_02"]

    assert len(result.rejected) == 2
    rows_rejected = {item["row"]: item["reason"] for item in result.rejected}
    assert 2 in rows_rejected
    assert "Missing coordinates" in rows_rejected[2]
    assert 3 in rows_rejected
    assert "Unknown or missing category" in rows_rejected[3]


def test_criterion_4_duplicate_ids_not_duplicated(tmp_path: Path) -> None:
    """Критерий 4: Повторный импорт того же файла не создаёт дублей (по id)."""
    csv_content = (
        "id,category,text,lat,lon\n"
        "r001,pothole,Яма номер 1,47.01,28.84\n"
        "r001,pothole,Яма номер 1 дубль,47.01,28.84\n"
        "r002,pothole,Яма номер 2,47.02,28.85\n"
    )
    csv_file = tmp_path / "dup.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    result = ingest.parse_file(csv_file)
    assert len(result.reports) == 2
    assert [r.id for r in result.reports] == ["r001", "r002"]


# ==============================================================================
# 2. Тесты API роутов (/api/v1/reports)
# ==============================================================================


def test_route_import_without_token_returns_401(client: TestClient) -> None:
    """POST /reports/import без токена возвращает 401."""
    files = {"file": ("data.json", b'{"reports": []}', "application/json")}
    response = client.post("/api/v1/reports/import", files=files)
    assert response.status_code == 401


def test_route_import_with_citizen_role_returns_403(client: TestClient) -> None:
    """POST /reports/import с ролью citizen возвращает 403."""
    citizen_user = User(
        email="citizen@example.com",
        role="citizen",
        is_active=True,
        is_superuser=False,
    )
    app.dependency_overrides[get_current_user] = lambda: citizen_user
    try:
        files = {"file": ("data.json", b'{"reports": []}', "application/json")}
        headers = {"Authorization": "Bearer mock_token"}
        response = client.post("/api/v1/reports/import", files=files, headers=headers)
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_route_import_with_supervisor_success(client: TestClient) -> None:
    """POST /reports/import с ролью supervisor возвращает 200 и {imported, rejected}."""
    supervisor_user = User(
        email="supervisor@example.com",
        role="supervisor",
        is_active=True,
        is_superuser=False,
    )
    app.dependency_overrides[get_current_user] = lambda: supervisor_user
    try:
        data_json = json.dumps(
            {
                "reports": [
                    {
                        "id": "imp_01",
                        "category": "manhole",
                        "text": "Открыт люк",
                        "location": {"lat": 47.01, "lon": 28.84},
                    },
                    {
                        "id": "imp_bad",
                        "category": "invalid_cat",
                        "text": "Ошибка категории",
                        "location": {"lat": 47.01, "lon": 28.84},
                    },
                ]
            }
        ).encode("utf-8")

        files = {"file": ("import.json", data_json, "application/json")}
        headers = {"Authorization": "Bearer mock_token"}
        response = client.post("/api/v1/reports/import", files=files, headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["imported"] == 1
        assert len(body["rejected"]) == 1
        assert body["rejected"][0]["row"] == 2
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_route_get_reports_and_filters(client: TestClient) -> None:
    """GET /reports отдаёт список обращений и поддерживает фильтры."""
    # Все обращения (16 из fixture)
    res = client.get("/api/v1/reports")
    assert res.status_code == 200
    all_reports = res.json()
    assert len(all_reports) == 16

    # Фильтр по статусу
    res_resolved = client.get("/api/v1/reports?status=resolved")
    assert res_resolved.status_code == 200
    resolved = res_resolved.json()
    assert len(resolved) == 1
    assert resolved[0]["id"] == "r016"

    # Фильтр по категории
    res_manhole = client.get("/api/v1/reports?category=manhole")
    assert res_manhole.status_code == 200
    manholes = res_manhole.json()
    assert len(manholes) == 1
    assert manholes[0]["id"] == "r011"

    # Фильтр по bbox (Albișoara район)
    res_bbox = client.get("/api/v1/reports?bbox=28.83,47.03,28.85,47.04")
    assert res_bbox.status_code == 200
    bbox_reports = res_bbox.json()
    assert len(bbox_reports) > 0
    assert all("r00" in r["id"] or "r01" in r["id"] for r in bbox_reports)


def test_route_create_report_sets_unverified(client: TestClient) -> None:
    """POST /reports создаёт обращение с verification.status='unverified'."""
    new_report_payload = {
        "id": "citizen_new_1",
        "source": "citizen",
        "category": "pothole",
        "text": "Яма возле подъезда",
        "location": {"lat": 47.02, "lon": 28.85},
        "created_at": datetime.now(UTC).isoformat(),
        "status": "open",
    }
    response = client.post("/api/v1/reports", json=new_report_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "citizen_new_1"
    assert data["verification"]["status"] == "unverified"

    # Проверяем, что появилось в GET /reports
    get_res = client.get("/api/v1/reports")
    ids = [r["id"] for r in get_res.json()]
    assert "citizen_new_1" in ids


def test_route_confirm_report_increments_confirmations(client: TestClient) -> None:
    """POST /reports/{id}/confirm увеличивает confirmations на 1."""
    # r001 в demo_city имеет confirmations: 5
    response = client.post("/api/v1/reports/r001/confirm")
    assert response.status_code == 200
    body = response.json()
    assert body["confirmations"] == 6

    # Повторное подтверждение
    response2 = client.post("/api/v1/reports/r001/confirm")
    assert response2.status_code == 200
    assert response2.json()["confirmations"] == 7


def test_route_confirm_nonexistent_returns_404(client: TestClient) -> None:
    """POST /reports/{id}/confirm с несуществующим id возвращает 404."""
    response = client.post("/api/v1/reports/nonexistent_999/confirm")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_route_create_invalid_body_returns_422(client: TestClient) -> None:
    """POST /reports с кривым телом возвращает 422."""
    response = client.post("/api/v1/reports", json={"invalid": "payload"})
    assert response.status_code == 422


# ==============================================================================
# 3. QA Чеклист (Мутации, Границы, Откат L0, Детерминированность)
# ==============================================================================


def test_qa_determinism() -> None:
    """QA 5: Два вызова подряд дают абсолютно одинаковый результат."""
    call1 = ingest.load_fixture()
    call2 = ingest.load_fixture()
    assert len(call1) == len(call2)
    assert [r.id for r in call1] == [r.id for r in call2]
    assert [r.location.lat for r in call1] == [r.location.lat for r in call2]


def test_qa_data_boundaries_empty_and_single(tmp_path: Path) -> None:
    """QA 3: Границы данных: пустой файл, 1 элемент, None в опциональных полях."""
    # Пустой файл
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("", encoding="utf-8")
    result_empty = ingest.parse_file(empty_file)
    assert len(result_empty.reports) == 0
    assert len(result_empty.rejected) == 0

    # Один элемент с None в опциональных полях
    single_json = tmp_path / "single.json"
    single_json.write_text(
        json.dumps(
            [
                {
                    "id": "r_single",
                    "category": "tree",
                    "text": "Упавшая ветка",
                    "location": {"lat": 47.01, "lon": 28.82},
                    "address": None,
                    "photo_url": None,
                    "created_at": "2026-09-22T08:00:00+00:00",
                }
            ]
        ),
        encoding="utf-8",
    )
    result_single = ingest.parse_file(single_json)
    assert len(result_single.reports) == 1
    r = result_single.reports[0]
    assert r.id == "r_single"
    assert r.address is None
    assert r.photo_url is None


def test_qa_fallback_to_l0_on_l1_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """QA 4: При сбое L1 происходит тихий откат на L0 и пишется warning."""
    monkeypatch.setattr(settings, "USE_MOCK", False)

    def l1_boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("L1 parser exploded")

    monkeypatch.setattr(ingest.l1, "parse_file", l1_boom)

    # Вызов должен не упасть, а тихо вернуть L0
    sample_file = tmp_path / "fallback.json"
    sample_file.write_text(
        json.dumps(
            [
                {
                    "id": "f1",
                    "category": "pothole",
                    "text": "Яма",
                    "location": {"lat": 47.01, "lon": 28.84},
                }
            ]
        ),
        encoding="utf-8",
    )

    res = ingest.parse_file(sample_file)
    assert len(res.reports) == 1
    assert res.reports[0].id == "f1"


# ==============================================================================
# 4. Тесты уровня L1 (маппинг, синонимы RO/RU/EN, fallback)
# ==============================================================================


def test_l1_all_8_categories_resolved_from_ro_ru_en() -> None:
    """L1: Проверка приведения категорий на румынском, русском и английском к CATEGORIES."""
    cases = [
        # pothole
        ("groapă", "pothole"),
        ("groapa", "pothole"),
        ("яма", "pothole"),
        ("выбоина", "pothole"),
        ("road_damage", "pothole"),
        # streetlight
        ("felinar", "streetlight"),
        ("iluminat_stradal", "streetlight"),
        ("освещение", "streetlight"),
        ("уличный_фонарь", "streetlight"),
        ("lighting", "streetlight"),
        # garbage
        ("gunoi", "garbage"),
        ("deșeuri", "garbage"),
        ("deseuri", "garbage"),
        ("мусор", "garbage"),
        ("свалка", "garbage"),
        ("trash", "garbage"),
        # manhole
        ("gura_de_canal", "manhole"),
        ("gură_de_canal", "manhole"),
        ("люк", "manhole"),
        ("открытый_люк", "manhole"),
        ("sewer_cover", "manhole"),
        # tree
        ("copac", "tree"),
        ("creangă_căzută", "tree"),
        ("дерево", "tree"),
        ("ветка", "tree"),
        ("fallen_tree", "tree"),
        # water_leak
        ("scurgere_apa", "water_leak"),
        ("țeavă_spartă", "water_leak"),
        ("утечка_воды", "water_leak"),
        ("прорыв_трубы", "water_leak"),
        ("pipe_burst", "water_leak"),
        # traffic_sign
        ("indicator_rutier", "traffic_sign"),
        ("semafor", "traffic_sign"),
        ("дорожный_знак", "traffic_sign"),
        ("светофор", "traffic_sign"),
        ("traffic_light", "traffic_sign"),
        # public_space
        ("spatiu_public", "public_space"),
        ("teren_de_joacă", "public_space"),
        ("сквер", "public_space"),
        ("скамейка", "public_space"),
        ("playground", "public_space"),
    ]

    for raw_cat, expected in cases:
        resolved = ingest.l1.resolve_category(raw_cat)
        assert resolved == expected, (
            f"Expected '{expected}' for '{raw_cat}', got '{resolved}'"
        )


def test_l1_csv_parsing_with_default_mapping_yaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """L1: CSV парсится с базовым mapping.yaml и синонимами без явной передачи mapping."""
    monkeypatch.setattr(settings, "USE_MOCK", False)

    csv_data = (
        "identificator,tip,descriere,latitudine,longitudine,locatie_adresa\n"
        "ro_01,groapa,Groapa adanca pe drum,47.012,28.825,str. Mateevici 10\n"
        "ru_01,открытый_люк,Крышка люка отсутствует,47.013,28.826,ул. Пушкина 5\n"
        "en_01,trash,Overflowing garbage bin,47.014,28.827,Main St 1\n"
    )
    f = tmp_path / "l1_test.csv"
    f.write_text(csv_data, encoding="utf-8")

    result = ingest.parse_file(f)
    assert len(result.rejected) == 0
    assert len(result.reports) == 3

    r1, r2, r3 = result.reports
    assert r1.id == "ro_01"
    assert r1.category == "pothole"
    assert r1.location.lat == 47.012
    assert r1.address == "str. Mateevici 10"

    assert r2.id == "ru_01"
    assert r2.category == "manhole"
    assert r2.text == "Крышка люка отсутствует"

    assert r3.id == "en_01"
    assert r3.category == "garbage"


def test_l1_json_parsing_with_rejected_rows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """L1: JSON с некорректными записями добавляет строки в rejected с указанием причины."""
    monkeypatch.setattr(settings, "USE_MOCK", False)

    json_data = [
        {
            "id": "valid_1",
            "категория": "яма",
            "текст": "Выбоина на дороге",
            "широта": 47.05,
            "долгота": 28.88,
        },
        {
            "id": "no_coords",
            "категория": "мусор",
            "текст": "Куча мусора",
            "широта": None,
            "долгота": None,
        },
        {
            "id": "unknown_cat",
            "категория": "космический_корабль",
            "текст": "НЛО приземлилось",
            "широта": 47.06,
            "долгота": 28.89,
        },
    ]
    f = tmp_path / "l1_test.json"
    f.write_text(json.dumps(json_data), encoding="utf-8")

    result = ingest.parse_file(f)
    assert len(result.reports) == 1
    assert result.reports[0].id == "valid_1"
    assert result.reports[0].category == "pothole"

    assert len(result.rejected) == 2
    rej_rows = {item["row"]: item["reason"] for item in result.rejected}
    assert 2 in rej_rows
    assert "Missing coordinates" in rej_rows[2]
    assert 3 in rej_rows
    assert "Unknown category" in rej_rows[3]


def test_l1_normalize_raises_clear_value_error() -> None:
    """L1: normalize() выбрасывает понятный ValueError при некорректных данных."""
    # Неизвестная категория
    with pytest.raises(ValueError, match="Unknown category"):
        ingest.l1.normalize(
            {
                "id": "err1",
                "category": "unknown_nonsense",
                "text": "Текст",
                "lat": 47.0,
                "lon": 28.0,
            }
        )

    # Отсутствуют координаты
    with pytest.raises(ValueError, match="Missing coordinates"):
        ingest.l1.normalize(
            {
                "id": "err2",
                "category": "pothole",
                "text": "Текст",
            }
        )

    # Пустой текст
    with pytest.raises(ValueError, match="Missing or empty report text"):
        ingest.l1.normalize(
            {
                "id": "err3",
                "category": "pothole",
                "text": "   ",
                "lat": 47.0,
                "lon": 28.0,
            }
        )
