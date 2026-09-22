"""L0: детерминированно, без сети, без ключей, без базы. Одни данные → один и тот же результат."""

from app.contracts.models import Cluster, Context, Priority, Report

_BASE_BY_CATEGORY = {"manhole": 0.9, "tree": 0.7, "pothole": 0.5}  # числа — из таблицы контракта, не выдумывать


def score(cluster: Cluster, reports: list[Report], ctx: Context) -> Priority:
    base = _BASE_BY_CATEGORY.get(cluster.category, 0.2)
    demand = min(1.0, (len(reports) + sum(r.confirmations for r in reports)) / 10)
    total = round(100 * (0.7 * base + 0.3 * demand), 1)
    return Priority(
        cluster_id=cluster.id,
        score=total,
        factors=[],  # в реальном блоке — список Factor по контракту
        confidence=1.0,
        needs_review=False,
    )
