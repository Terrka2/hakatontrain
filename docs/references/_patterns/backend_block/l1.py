"""L1: целевая реализация. Может ходить в сеть/базу — с таймаутом ≤ 5 с и максимум одним повтором.

Ошибки НЕ ловим здесь: их ловит порт в __init__.py и откатывается на L0.
"""

import httpx

from app.contracts.models import Cluster, Context, Priority, Report
from app.core.config import settings

from . import l0


def score(cluster: Cluster, reports: list[Report], ctx: Context) -> Priority:
    base = l0.score(cluster, reports, ctx)
    with httpx.Client(timeout=5.0) as client:  # внешний вызов — только так: таймаут явно
        resp = client.get(f"{settings.EXTERNAL_URL}/risk", params={"category": cluster.category})
        resp.raise_for_status()
    risk = float(resp.json()["risk"])
    return base.model_copy(update={"score": min(100.0, base.score + 10 * risk)})
