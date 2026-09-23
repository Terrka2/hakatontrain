"""Фактор EX · Мероприятия (блок X1)."""

from datetime import UTC, datetime

from app.blocks.events.l0 import haversine_m
from app.contracts.models import Cluster, Context, Report


def _to_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def evaluate(
    cluster: Cluster,
    _reports: list[Report],
    _history: list[Report],
    ctx: Context,
) -> tuple[float | None, list[str]]:
    if not ctx.events:
        return None, []

    now_utc = _to_utc(ctx.now)
    matches: list[tuple[float, str, int, int]] = []

    for ev in ctx.events:
        ev_start = _to_utc(ev.starts_at)
        ev_end = _to_utc(ev.ends_at)
        hours_to_start = (ev_start - now_utc).total_seconds() / 3600.0

        if hours_to_start <= 72.0 and ev_end >= now_utc:
            dist = haversine_m(cluster.centroid, ev.location)
            if dist <= ev.radius_m:
                score = min(1.0, ev.expected_people / 1000.0)
                matches.append((score, ev.title, ev.radius_m, ev.expected_people))

    if not matches:
        return 0.0, []

    matches.sort(key=lambda m: m[0], reverse=True)
    best_score, title, radius, people = matches[0]
    return best_score, [f"Мероприятие в радиусе {radius}м: {title} ({people} чел.)"]
