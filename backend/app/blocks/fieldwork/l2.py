"""Уровень L2 блока B8: геофенсинг бригады при отметке статуса."""

import logging
from typing import Any

from app.blocks import geo
from app.blocks.fieldwork import l1
from app.contracts import models
from app.db import Repository, get_repository

log = logging.getLogger(__name__)


def check_geofence(
    update: models.JobUpdate, stop: models.RouteStop
) -> tuple[bool, float | None]:
    """Проверка геометки бригады.

    - Если update.location is None -> вернуть (True, None) (нет данных — не блокируем).
    - Иначе: вычислить расстояние через app.blocks.geo.haversine_m(update.location, stop.location).
    - Если расстояние > 200 м -> вернуть (False, distance_m).
    - Иначе -> вернуть (True, distance_m).
    """
    if update.location is None:
        return True, None
    dist = geo.haversine_m(update.location, stop.location)
    if dist > 200.0:
        return False, dist
    return True, dist


def apply_update_with_geofence(
    update: models.JobUpdate,
    db: Any = None,
    repo: Repository | None = None,
) -> models.RouteStop:
    """Применяет обновление статуса с проверкой геофенсинга.

    - Находит остановку по job_id.
    - Вызывает check_geofence.
    - Если False: логирует предупреждение и дописывает в update.note (Geofence: {dist:.0f}m от остановки).
    - Вызывает l1.apply_update(update, repo=r).
    """
    r: Repository
    if repo is not None:
        r = repo
    elif db is not None:
        r = db
    else:
        r = get_repository()

    plan = r.current_plan(status="approved")
    if not plan:
        return l1.apply_update(update, repo=r)

    pair = [
        (route, s)
        for route in plan.routes
        for s in route.stops
        if s.job_id == update.job_id
    ]
    if not pair:
        return l1.apply_update(update, repo=r)

    _route, stop = pair[0]
    ok, dist = check_geofence(update, stop)
    if not ok and dist is not None:
        log.warning(
            "Geofence violation: crew %s is %.0f m from stop %s",
            update.crew_id,
            dist,
            update.job_id,
        )
        msg = f"Geofence: {dist:.0f}m от остановки"
        if update.note and update.note.strip():
            update.note = f"{update.note}; {msg}"
        else:
            update.note = msg

    return l1.apply_update(update, repo=r)
