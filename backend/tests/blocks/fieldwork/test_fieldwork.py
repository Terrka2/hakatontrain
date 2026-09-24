"""Тесты блока B8 (fieldwork) уровень L0 на критерии приёмки 1-5 и граничные случаи."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.blocks.fieldwork import apply_update, get_crew_route, l0, progress
from app.contracts.models import JobUpdate


@pytest.fixture(autouse=True)
def _reset_fieldwork_state() -> None:
    l0.reset_state()


def test_criterion_1_crew_sees_only_own_stops_and_only_approved_plan() -> None:
    """1. Бригада c1 видит только свои остановки и только из утверждённого плана;

    при одном лишь черновике — пустой маршрут с понятным сообщением.
    """
    route_c1 = get_crew_route("c1")
    assert route_c1 is not None
    assert route_c1.crew_id == "c1"
    # Бригада c1 видит только свои работы
    stop_job_ids = [s.job_id for s in route_c1.stops]
    assert stop_job_ids == ["job_c1_1", "job_c1_2"]
    assert "job_c2_1" not in stop_job_ids
    assert "job_c2_2" not in stop_job_ids

    # При черновике плана — get_crew_route возвращает None
    assert l0._plan is not None
    draft_plan = l0._plan.model_copy(update={"status": "draft"})
    l0.set_plan(draft_plan)
    assert get_crew_route("c1") is None

    # При отсутствии плана вообще
    l0.set_plan(None)
    assert get_crew_route("c1") is None


def test_criterion_2_done_with_photo_resolves_stop_clusters_and_reports() -> None:
    """2. `done` с фото → остановка `done`, кластеры задачи `resolved`."""
    # pending -> arrived
    up_arrive = JobUpdate(
        job_id="job_c1_1",
        crew_id="c1",
        status="arrived",
        at=datetime(2026, 9, 26, 8, 30, tzinfo=UTC),
    )
    stop_arr = apply_update(up_arrive)
    assert stop_arr.status == "arrived"

    # arrived -> done с фото
    up_done = JobUpdate(
        job_id="job_c1_1",
        crew_id="c1",
        status="done",
        at=datetime(2026, 9, 26, 9, 0, tzinfo=UTC),
        photo_url="https://storage.city.md/photos/done_1.jpg",
    )
    stop_done = apply_update(up_done)
    assert stop_done.status == "done"

    # Кластер связанной задачи стал resolved
    cl = l0.get_cluster("cl_001")
    assert cl is not None
    assert cl.status == "resolved"

    # Все обращения в этом кластере стали resolved
    for rid in cl.report_ids:
        rep = l0.get_report(rid)
        assert rep is not None
        assert rep.status == "resolved"


def test_criterion_3_validation_and_transitions_protect_state() -> None:
    """3. `done` без фото, `failed` без причины, переход `done → arrived`

    → ошибки 422 / 409, данные не изменились.
    """
    # 3.1: pending -> done напрямую запрещено (409)
    up_pending_to_done = JobUpdate(
        job_id="job_c1_1",
        crew_id="c1",
        status="done",
        at=datetime(2026, 9, 26, 8, 30, tzinfo=UTC),
        photo_url="https://example.com/p.jpg",
    )
    with pytest.raises(HTTPException) as exc:
        apply_update(up_pending_to_done)
    assert exc.value.status_code == 409
    route = get_crew_route("c1")
    assert route is not None
    assert route.stops[0].status == "pending"

    # Переводим в arrived
    apply_update(
        JobUpdate(
            job_id="job_c1_1",
            crew_id="c1",
            status="arrived",
            at=datetime(2026, 9, 26, 8, 30, tzinfo=UTC),
        )
    )

    # 3.2: done без фото → 422, данные не меняются
    up_done_no_photo = JobUpdate(
        job_id="job_c1_1",
        crew_id="c1",
        status="done",
        at=datetime(2026, 9, 26, 9, 0, tzinfo=UTC),
        photo_url=None,
    )
    with pytest.raises(HTTPException) as exc:
        apply_update(up_done_no_photo)
    assert exc.value.status_code == 422
    route = get_crew_route("c1")
    assert route is not None
    assert route.stops[0].status == "arrived"
    cl = l0.get_cluster("cl_001")
    assert cl is not None
    assert cl.status == "open"

    # 3.3: failed без причины → 422, данные не меняются
    up_failed_no_reason = JobUpdate(
        job_id="job_c1_1",
        crew_id="c1",
        status="failed",
        at=datetime(2026, 9, 26, 9, 0, tzinfo=UTC),
        reason=None,
    )
    with pytest.raises(HTTPException) as exc:
        apply_update(up_failed_no_reason)
    assert exc.value.status_code == 422
    route = get_crew_route("c1")
    assert route is not None
    assert route.stops[0].status == "arrived"

    # 3.4: failed с needs_other_skill без needs_skill → 422
    up_failed_no_skill = JobUpdate(
        job_id="job_c1_1",
        crew_id="c1",
        status="failed",
        at=datetime(2026, 9, 26, 9, 0, tzinfo=UTC),
        reason="needs_other_skill",
        needs_skill=None,
    )
    with pytest.raises(HTTPException) as exc:
        apply_update(up_failed_no_skill)
    assert exc.value.status_code == 422
    route = get_crew_route("c1")
    assert route is not None
    assert route.stops[0].status == "arrived"

    # Успешно переводим в done
    apply_update(
        JobUpdate(
            job_id="job_c1_1",
            crew_id="c1",
            status="done",
            at=datetime(2026, 9, 26, 9, 0, tzinfo=UTC),
            photo_url="https://example.com/p.jpg",
        )
    )
    route = get_crew_route("c1")
    assert route is not None
    assert route.stops[0].status == "done"

    # 3.5: переход done → arrived → 409, статус остаётся done
    with pytest.raises(HTTPException) as exc:
        apply_update(
            JobUpdate(
                job_id="job_c1_1",
                crew_id="c1",
                status="arrived",
                at=datetime(2026, 9, 26, 9, 5, tzinfo=UTC),
            )
        )
    assert exc.value.status_code == 409
    route = get_crew_route("c1")
    assert route is not None
    assert route.stops[0].status == "done"


def test_criterion_4_failed_triggers_operator_run_once() -> None:
    """4. `failed` → зафиксирован вызов `operator_run("job_update", …)` (в тесте — мок) ровно один раз."""
    with patch("app.blocks.operator.operator_run") as mock_operator_run:
        up = JobUpdate(
            job_id="job_c1_1",
            crew_id="c1",
            status="failed",
            at=datetime(2026, 9, 26, 9, 0, tzinfo=UTC),
            reason="weather",
            note="Сильный ливень, работы отложены",
        )
        stop = apply_update(up)
        assert stop.status == "failed"
        mock_operator_run.assert_called_once_with("job_update", up.at, job_update=up)


def test_criterion_5_crew_c1_cannot_update_c2_stop() -> None:
    """5. Бригада c1 не может отметить задачу бригады c2 → 403."""
    # job_c2_1 принадлежит c2
    up = JobUpdate(
        job_id="job_c2_1",
        crew_id="c1",
        status="arrived",
        at=datetime(2026, 9, 26, 8, 30, tzinfo=UTC),
    )
    with pytest.raises(HTTPException) as exc:
        apply_update(up)
    assert exc.value.status_code == 403


def test_progress_and_boundaries() -> None:
    """Проверка progress, детерминированности и неизвестных id."""
    prog = progress("plan_demo")
    assert "c1" in prog
    assert prog["c1"]["pending"] == 2
    assert prog["c1"]["done"] == 0

    # Обновляем остановку
    apply_update(
        JobUpdate(
            job_id="job_c1_1",
            crew_id="c1",
            status="arrived",
            at=datetime(2026, 9, 26, 8, 30, tzinfo=UTC),
        )
    )
    prog_after = progress("plan_demo")
    assert prog_after["c1"]["arrived"] == 1
    assert prog_after["c1"]["pending"] == 1

    # Несуществующий plan_id
    assert progress("non_existent_plan") == {}

    # Неизвестная бригада
    assert get_crew_route("non_existent_crew") is None

    # Неизвестный job_id
    with pytest.raises(HTTPException) as exc:
        apply_update(
            JobUpdate(
                job_id="non_existent_job",
                crew_id="c1",
                status="arrived",
                at=datetime(2026, 9, 26, 8, 30, tzinfo=UTC),
            )
        )
    assert exc.value.status_code == 404

    # Детерминированность get_crew_route
    r1 = get_crew_route("c2")
    r2 = get_crew_route("c2")
    assert r1 == r2
