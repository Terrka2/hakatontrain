"""Фактор AG: Возраст проблемы (вес 0.15). min(1, дней с first_reported_at / 14)."""

from app.contracts.models import Cluster, Context, Report


def evaluate(
    cluster: Cluster, reports: list[Report], history: list[Report], ctx: Context
) -> tuple[float | None, list[str]]:
    _ = (reports, history)
    delta_sec = (ctx.now - cluster.first_reported_at).total_seconds()
    days = max(0.0, delta_sec / 86400.0)
    score = min(1.0, max(0.0, days / 14.0))
    return (round(score, 4), [f"Возраст проблемы: {days:.1f} дн. (из 14 дн.)"])
