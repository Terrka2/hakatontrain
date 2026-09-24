"""Фактор RC: Повтор (вес 0.10).

В history есть решённое обращение той же категории <= 60 м за 12 мес -> 1.0, иначе 0.
Пустая history -> None.
"""

from app.contracts.models import Cluster, Context, Report

from ..geo_utils import haversine_m


def evaluate(
    cluster: Cluster, reports: list[Report], history: list[Report], ctx: Context
) -> tuple[float | None, list[str]]:
    _ = (reports, ctx)
    if not history:
        return (None, [])

    cluster_time = cluster.first_reported_at
    cat = cluster.category.lower()

    for h in history:
        if h.status != "resolved" or h.category.lower() != cat:
            continue

        diff_days = (cluster_time - h.created_at).total_seconds() / 86400.0
        if 0.0 <= diff_days <= 366.0:
            dist = haversine_m(cluster.centroid, h.location)
            if dist <= 60.0:
                return (
                    1.0,
                    [
                        f"Решённое обращение {h.id} той же категории в {dist:.0f} м (за последние 12 мес.)"
                    ],
                )

    return (0.0, [])
