"""Уровень L0 блока X1: городские мероприятия из fixture demo_city.json."""

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.contracts import models
from app.core.config import settings

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "demo_city.json"

_events: list[models.Event] = []


def _to_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def haversine_m(p1: models.GeoPoint, p2: models.GeoPoint) -> float:
    r = 6371000.0
    lat1, lon1 = math.radians(p1.lat), math.radians(p1.lon)
    lat2, lon2 = math.radians(p2.lat), math.radians(p2.lon)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def reset_state() -> None:
    global _events
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    _events = [models.Event(**e) for e in data.get("events", [])]


reset_state()


def add_event(event: models.Event) -> models.Event:
    _events.append(event.model_copy(deep=True))
    return event.model_copy(deep=True)


def get_events(start: datetime, end: datetime) -> list[models.Event]:
    s_utc, e_utc = _to_utc(start), _to_utc(end)
    return [
        e.model_copy(deep=True)
        for e in _events
        if _to_utc(e.starts_at) <= e_utc and _to_utc(e.ends_at) >= s_utc
    ]


def enrich_context(ctx: models.Context) -> models.Context:
    if settings.OPTIONAL_BLOCKS != "on":
        ctx.events = []
        return ctx
    ctx.events = get_events(ctx.now, ctx.now + timedelta(hours=72))
    return ctx


def apply_deadlines(
    jobs: list[models.Job],
    clusters: list[models.Cluster],
    events: list[models.Event],
) -> tuple[list[models.Job], list[models.Decision]]:
    cluster_map = {c.id: c for c in clusters}
    updated_jobs: list[models.Job] = []
    decisions: list[models.Decision] = []

    for job in jobs:
        j = job.model_copy(deep=True)
        locs = [j.location] + [
            cluster_map[cid].centroid for cid in j.cluster_ids if cid in cluster_map
        ]
        matches = [
            (ev.starts_at, ev.title)
            for ev in events
            if any(haversine_m(loc, ev.location) <= ev.radius_m for loc in locs)
        ]
        if matches:
            matches.sort(key=lambda x: x[0])
            start_dt, title = matches[0]
            if j.deadline is None or start_dt < j.deadline:
                j.deadline = start_dt
                decisions.append(
                    models.Decision(
                        kind="deadline",
                        subject_id=j.id,
                        reason=f"Дедлайн до начала мероприятия: {title}",
                        by="rule",
                    )
                )
        updated_jobs.append(j)

    return updated_jobs, decisions
