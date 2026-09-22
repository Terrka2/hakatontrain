"""Фактор DM: Спрос (вес 0.15). min(1, (кол-во обращений + сумма confirmations) / 10)."""

from app.contracts.models import Cluster, Context, Report


def evaluate(
    cluster: Cluster, reports: list[Report], history: list[Report], ctx: Context
) -> tuple[float | None, list[str]]:
    _ = (history, ctx)
    n = len(reports) if reports else len(cluster.report_ids)
    conf = sum(r.confirmations for r in reports) if reports else 0
    score = min(1.0, max(0.0, (n + conf) / 10.0))
    return (
        round(score, 4),
        [f"Обращений в кластере: {n}, подтверждений жителей: {conf}"],
    )
