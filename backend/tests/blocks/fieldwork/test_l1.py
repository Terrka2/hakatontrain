"""Тесты уровня L1 блока B8: репозиторий D1, загрузка фото, откат на L0."""

import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.blocks.fieldwork as fieldwork
from app.api.deps import get_current_user
from app.blocks.fieldwork import l0, l1
from app.contracts import models
from app.core.config import settings
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
        id="plan_test",
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
                        status="pending",
                    ),
                ],
            ),
            models.CrewRoute(
                crew_id="c2",
                stops=[
                    models.RouteStop(
                        job_id="job_c2_1",
                        location=loc,
                        arrival=t0,
                        departure=t0,
                        status="pending",
                    )
                ],
            ),
        ],
    )


def test_l1_get_crew_route_mock_repo() -> None:
    repo = MagicMock()
    plan = build_test_plan()
    repo.current_plan.return_value = plan

    route = l1.get_crew_route("c1", repo=repo)
    assert route is not None
    assert route.crew_id == "c1"
    assert len(route.stops) == 2

    assert l1.get_crew_route("unknown", repo=repo) is None

    repo.current_plan.return_value = None
    assert l1.get_crew_route("c1", repo=repo) is None


def test_l1_apply_update_transitions_and_d1_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = MagicMock()
    plan = build_test_plan()
    repo.current_plan.return_value = plan

    t = datetime.now(UTC)
    loc = models.GeoPoint(lat=55.75, lon=37.61)
    c_mock = models.Cluster(
        id="cl_001",
        category="pothole",
        centroid=loc,
        report_ids=["r001"],
        first_reported_at=t,
        last_reported_at=t,
    )
    p_mock = models.Priority(
        cluster_id="cl_001",
        score=80.0,
        factors=[],
        confidence=1.0,
    )
    rep_mock = models.Report(
        id="r001",
        category="pothole",
        text="Яма",
        created_at=t,
        location=loc,
        status="open",
    )

    repo.list_clusters.return_value = [(c_mock, p_mock)]
    repo.list_reports.return_value = [rep_mock]

    # 1. pending -> arrived
    u1 = models.JobUpdate(job_id="job_c1_1", crew_id="c1", status="arrived", at=t)
    s1 = l1.apply_update(u1, repo=repo)
    assert s1.status == "arrived"
    repo.set_stop_status.assert_called_with("plan_test", "job_c1_1", "arrived")

    # 2. arrived -> done (with photo_url)
    u2 = models.JobUpdate(
        job_id="job_c1_1",
        crew_id="c1",
        status="done",
        at=t,
        photo_url="https://img.test/proof.jpg",
    )
    s2 = l1.apply_update(u2, repo=repo)
    assert s2.status == "done"
    repo.set_stop_status.assert_called_with("plan_test", "job_c1_1", "done")
    repo.save_clusters.assert_called()
    repo.upsert_reports.assert_called()

    # 3. pending -> failed (with reason)
    op_mock = MagicMock()
    monkeypatch.setattr("app.blocks.operator.operator_run", op_mock)
    u3 = models.JobUpdate(
        job_id="job_c1_2",
        crew_id="c1",
        status="failed",
        at=t,
        reason="no_access",
    )
    s3 = l1.apply_update(u3, repo=repo)
    assert s3.status == "failed"
    op_mock.assert_called_once()


def test_l1_apply_update_error_validations() -> None:
    repo = MagicMock()
    plan = build_test_plan()
    repo.current_plan.return_value = plan
    t = datetime.now(UTC)

    # 403: wrong crew
    with pytest.raises(HTTPException) as exc:
        l1.apply_update(
            models.JobUpdate(job_id="job_c1_1", crew_id="c2", status="arrived", at=t),
            repo=repo,
        )
    assert exc.value.status_code == 403

    # 409: pending -> done directly without photo/arrived
    with pytest.raises(HTTPException) as exc:
        l1.apply_update(
            models.JobUpdate(job_id="job_c1_1", crew_id="c1", status="done", at=t),
            repo=repo,
        )
    assert exc.value.status_code in (409, 422)

    # 404: unknown job
    with pytest.raises(HTTPException) as exc:
        l1.apply_update(
            models.JobUpdate(
                job_id="job_unknown", crew_id="c1", status="arrived", at=t
            ),
            repo=repo,
        )
    assert exc.value.status_code == 404


def test_l1_progress() -> None:
    repo = MagicMock()
    plan = build_test_plan()
    plan.routes[0].stops[0].status = "done"
    plan.routes[0].stops[1].status = "arrived"
    repo.get_plan.return_value = plan

    pr = l1.progress("plan_test", repo=repo)
    assert pr["c1"]["done"] == 1
    assert pr["c1"]["arrived"] == 1
    assert pr["c1"]["pending"] == 0
    assert pr["c2"]["pending"] == 1

    repo.get_plan.return_value = None
    repo.current_plan.return_value = None
    assert l1.progress("unknown", repo=repo) == {}


def test_fallback_to_l0_when_l1_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    l0.reset_state()
    monkeypatch.setattr(settings, "USE_MOCK", False)

    def raise_db_err(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("Database connection refused")

    monkeypatch.setattr(l1, "get_crew_route", raise_db_err)
    monkeypatch.setattr(l1, "apply_update", raise_db_err)
    monkeypatch.setattr(l1, "progress", raise_db_err)

    # 1. get_crew_route falls back to L0
    with caplog.at_level("WARNING"):
        route = fieldwork.get_crew_route("c1")
    assert route is not None
    assert route.crew_id == "c1"
    assert "B8: L1 get_crew_route failed, falling back to L0" in caplog.text

    # 2. apply_update falls back to L0
    u = models.JobUpdate(
        job_id="job_c1_1", crew_id="c1", status="arrived", at=datetime.now(UTC)
    )
    with caplog.at_level("WARNING"):
        stop = fieldwork.apply_update(u)
    assert stop.status == "arrived"
    assert "B8: L1 apply_update failed, falling back to L0" in caplog.text

    # 3. progress falls back to L0
    with caplog.at_level("WARNING"):
        pr = fieldwork.progress("plan_demo")
    assert "c1" in pr
    assert "B8: L1 progress failed, falling back to L0" in caplog.text

    # 4. HTTPException is re-raised and NOT caught by fallback
    def raise_http_err(*_args: object, **_kwargs: object) -> None:
        raise HTTPException(409, "Conflict")

    monkeypatch.setattr(l1, "apply_update", raise_http_err)
    with pytest.raises(HTTPException) as exc:
        fieldwork.apply_update(u)
    assert exc.value.status_code == 409


def test_photo_upload_multipart_creates_file_and_updates_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    l0.reset_state()
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr("app.api.routes.crew.UPLOAD_DIR", upload_dir)
    app.dependency_overrides[get_current_user] = lambda: make_user("crew", "c1")

    # Step 1: mark arrived first
    r1 = client.post(
        f"{API_PREFIX}/jobs/job_c1_1/status",
        headers={"Authorization": "Bearer mock"},
        json={
            "job_id": "job_c1_1",
            "crew_id": "c1",
            "status": "arrived",
            "at": datetime.now(UTC).isoformat(),
        },
    )
    assert r1.status_code == 200

    # Step 2: mark done via multipart upload
    file_content = b"fake image binary content for test"
    files = {"photo": ("evidence.png", file_content, "image/png")}
    data = {
        "job_id": "job_c1_1",
        "crew_id": "c1",
        "status": "done",
        "at": datetime.now(UTC).isoformat(),
    }

    r2 = client.post(
        f"{API_PREFIX}/jobs/job_c1_1/status",
        headers={"Authorization": "Bearer mock"},
        data=data,
        files=files,
    )
    assert r2.status_code == 200
    stop_data = r2.json()
    assert stop_data["status"] == "done"

    # Check file exists on disk
    saved_files = list(upload_dir.glob("*.png"))
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == file_content
