"""Тесты уровня L2 блока B8: геофенсинг бригады, предупреждения в note и каскадный откат."""

import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.blocks.fieldwork as fieldwork
from app.api.deps import get_current_user
from app.blocks import geo
from app.blocks.fieldwork import l0, l2
from app.contracts import models
from app.core.config import settings
from app.db import get_repository
from app.main import app
from app.models import User

API_PREFIX = f"{settings.API_V1_STR}/crew"
client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_overrides() -> Generator[None]:
    app.dependency_overrides.clear()
    l0.reset_state()
    yield
    app.dependency_overrides.clear()
    l0.reset_state()


def make_user(role: str, crew_id: str | None = None) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role}@demo.md",
        role=role,
        crew_id=crew_id,
        is_active=True,
        is_superuser=False,
        hashed_password="mock",
    )


def build_test_plan() -> models.Plan:
    t0 = datetime(2026, 9, 26, 8, 0, tzinfo=UTC)
    loc = models.GeoPoint(lat=55.75, lon=37.61)
    return models.Plan(
        id="plan_test_l2",
        day=date(2026, 9, 26),
        status="approved",
        routes=[
            models.CrewRoute(
                crew_id="c1",
                stops=[
                    models.RouteStop(
                        job_id="job_c1_1",
                        location=loc,
                        arrival=t0,
                        departure=t0,
                        status="pending",
                    ),
                    models.RouteStop(
                        job_id="job_c1_2",
                        location=loc,
                        arrival=t0,
                        departure=t0,
                        status="arrived",
                    ),
                ],
            )
        ],
    )


def test_check_geofence_none_location() -> None:
    """1. При update.location is None геофенсинг не блокирует и возвращает (True, None)."""
    stop = models.RouteStop(
        job_id="job_1",
        location=models.GeoPoint(lat=55.75, lon=37.61),
        arrival=datetime.now(UTC),
        departure=datetime.now(UTC),
    )
    update = models.JobUpdate(
        job_id="job_1",
        crew_id="c1",
        status="arrived",
        at=datetime.now(UTC),
        location=None,
    )
    ok, dist = l2.check_geofence(update, stop)
    assert ok is True
    assert dist is None


def test_check_geofence_within_200m(monkeypatch: pytest.MonkeyPatch) -> None:
    """2. При расстоянии <= 200 м геофенсинг успешен и возвращает (True, distance_m)."""
    stop = models.RouteStop(
        job_id="job_1",
        location=models.GeoPoint(lat=55.75, lon=37.61),
        arrival=datetime.now(UTC),
        departure=datetime.now(UTC),
    )
    update = models.JobUpdate(
        job_id="job_1",
        crew_id="c1",
        status="arrived",
        at=datetime.now(UTC),
        location=models.GeoPoint(lat=55.751, lon=37.611),
    )

    monkeypatch.setattr(geo, "haversine_m", lambda _a, _b: 150.0)
    ok, dist = l2.check_geofence(update, stop)
    assert ok is True
    assert dist == 150.0

    monkeypatch.setattr(geo, "haversine_m", lambda _a, _b: 200.0)
    ok, dist = l2.check_geofence(update, stop)
    assert ok is True
    assert dist == 200.0


def test_check_geofence_exceeds_200m(monkeypatch: pytest.MonkeyPatch) -> None:
    """3. При расстоянии > 200 м геофенсинг возвращает (False, distance_m)."""
    stop = models.RouteStop(
        job_id="job_1",
        location=models.GeoPoint(lat=55.75, lon=37.61),
        arrival=datetime.now(UTC),
        departure=datetime.now(UTC),
    )
    update = models.JobUpdate(
        job_id="job_1",
        crew_id="c1",
        status="arrived",
        at=datetime.now(UTC),
        location=models.GeoPoint(lat=55.76, lon=37.62),
    )

    monkeypatch.setattr(geo, "haversine_m", lambda _a, _b: 200.1)
    ok, dist = l2.check_geofence(update, stop)
    assert ok is False
    assert dist == 200.1

    monkeypatch.setattr(geo, "haversine_m", lambda _a, _b: 520.4)
    ok, dist = l2.check_geofence(update, stop)
    assert ok is False
    assert dist == 520.4


def test_apply_update_geofence_violation_appends_note(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """4. Нарушение геофенсинга: логируется warning, в note пишется Geofence, операция не блокируется."""
    repo = MagicMock()
    plan = build_test_plan()
    repo.current_plan.return_value = plan
    monkeypatch.setattr(geo, "haversine_m", lambda _a, _b: 350.2)

    # Вариант A: исходный note пустой (None)
    update1 = models.JobUpdate(
        job_id="job_c1_1",
        crew_id="c1",
        status="arrived",
        at=datetime.now(UTC),
        location=models.GeoPoint(lat=55.80, lon=37.70),
        note=None,
    )
    with caplog.at_level("WARNING"):
        res1 = l2.apply_update_with_geofence(update1, repo=repo)

    assert res1.status == "arrived"
    assert update1.note == "Geofence: 350m от остановки"
    assert "Geofence violation: crew c1 is 350 m from stop job_c1_1" in caplog.text

    # Вариант B: исходный note уже содержит текст
    update2 = models.JobUpdate(
        job_id="job_c1_2",
        crew_id="c1",
        status="done",
        at=datetime.now(UTC),
        photo_url="https://photo.demo/test.jpg",
        location=models.GeoPoint(lat=55.80, lon=37.70),
        note="Работы выполнены",
    )
    repo.list_clusters.return_value = []
    res2 = l2.apply_update_with_geofence(update2, repo=repo)
    assert res2.status == "done"
    assert update2.note == "Работы выполнены; Geofence: 350m от остановки"


def test_apply_update_geofence_ok_does_not_modify_note(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """5. Расстояние < 200 м: note не меняется, предупреждение не логируется."""
    repo = MagicMock()
    plan = build_test_plan()
    repo.current_plan.return_value = plan
    monkeypatch.setattr(geo, "haversine_m", lambda _a, _b: 85.0)

    update = models.JobUpdate(
        job_id="job_c1_1",
        crew_id="c1",
        status="arrived",
        at=datetime.now(UTC),
        location=models.GeoPoint(lat=55.7505, lon=37.6105),
        note="Всё по плану",
    )
    with caplog.at_level("WARNING"):
        res = l2.apply_update_with_geofence(update, repo=repo)

    assert res.status == "arrived"
    assert update.note == "Всё по плану"
    assert "Geofence violation" not in caplog.text


def test_apply_update_l2_fallback_to_l1_on_l2_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """6. Ошибка в L2 (например, падение вычисления гео): откат на L1."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    repo = MagicMock()
    plan = build_test_plan()
    repo.current_plan.return_value = plan

    def raise_geo_err(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("GPS computation breakdown")

    monkeypatch.setattr(l2, "check_geofence", raise_geo_err)

    update = models.JobUpdate(
        job_id="job_c1_1",
        crew_id="c1",
        status="arrived",
        at=datetime.now(UTC),
        location=models.GeoPoint(lat=55.80, lon=37.70),
    )
    with caplog.at_level("WARNING"):
        res = fieldwork.apply_update(update, repo=repo)

    assert res.status == "arrived"
    assert "B8: L2 apply_update failed, falling back to L1" in caplog.text


def test_apply_update_l2_cascade_to_l0_on_d1_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """7. Каскадный откат: при ошибке D1 L2 -> L1 -> L0."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    l0.reset_state()

    repo = MagicMock()
    repo.current_plan.side_effect = RuntimeError("Database unreachable")

    update = models.JobUpdate(
        job_id="job_c1_1",
        crew_id="c1",
        status="arrived",
        at=datetime.now(UTC),
        location=models.GeoPoint(lat=55.80, lon=37.70),
    )
    with caplog.at_level("WARNING"):
        res = fieldwork.apply_update(update, repo=repo)

    assert res.status == "arrived"
    assert "B8: L2 apply_update failed, falling back to L1" in caplog.text
    assert "B8: L1 apply_update failed, falling back to L0" in caplog.text


def test_http_exception_not_masked_by_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """8. Валидационные и ролевые ошибки (HTTPException) не маскируются fallback."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    repo = MagicMock()
    plan = build_test_plan()
    repo.current_plan.return_value = plan

    # 403: чужая бригада c2 пытается изменить остановку c1
    u_403 = models.JobUpdate(
        job_id="job_c1_1",
        crew_id="c2",
        status="arrived",
        at=datetime.now(UTC),
    )
    with pytest.raises(HTTPException) as exc403:
        fieldwork.apply_update(u_403, repo=repo)
    assert exc403.value.status_code == 403

    # 409: недопустимый переход (arrived -> arrived)
    u_409 = models.JobUpdate(
        job_id="job_c1_2",
        crew_id="c1",
        status="arrived",
        at=datetime.now(UTC),
    )
    with pytest.raises(HTTPException) as exc409:
        fieldwork.apply_update(u_409, repo=repo)
    assert exc409.value.status_code == 409


def test_route_multipart_with_location_and_geofence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """9. Маршрут /crew/jobs/{job_id}/status принимает multipart с координатами и фото."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    repo = MagicMock()
    plan = build_test_plan()
    repo.current_plan.return_value = plan
    repo.list_clusters.return_value = []
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: make_user("crew", "c1")
    monkeypatch.setattr(geo, "haversine_m", lambda _a, _b: 400.0)

    # 1. Сначала arrived (job_c1_1: pending -> arrived)
    r_arr = client.post(
        f"{API_PREFIX}/jobs/job_c1_1/status",
        headers={"Authorization": "Bearer mock"},
        json={
            "job_id": "job_c1_1",
            "crew_id": "c1",
            "status": "arrived",
            "at": datetime.now(UTC).isoformat(),
        },
    )
    assert r_arr.status_code == 200

    # 2. Теперь done через multipart с координатами и фото
    data = {
        "job_id": "job_c1_1",
        "crew_id": "c1",
        "status": "done",
        "at": datetime.now(UTC).isoformat(),
        "lat": "55.80",
        "lon": "37.70",
        "note": "Уборка завершена",
    }
    files = {"photo": ("finish.jpg", b"jpeg_bytes_content", "image/jpeg")}
    r_done = client.post(
        f"{API_PREFIX}/jobs/job_c1_1/status",
        headers={"Authorization": "Bearer mock"},
        data=data,
        files=files,
    )
    assert r_done.status_code == 200
    res_data = r_done.json()
    assert res_data["status"] == "done"
