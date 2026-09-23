"""Фактор VF: Достоверность (вес 0.05).

Доля обращений с фото или verification.status in (plausible, confirmed).
"""

from app.contracts.models import Cluster, Context, Report

VALID_STATUSES = {"plausible", "confirmed"}


def evaluate(
    cluster: Cluster, reports: list[Report], history: list[Report], ctx: Context
) -> tuple[float | None, list[str]]:
    _ = (cluster, history, ctx)
    if not reports:
        return (0.0, [])

    verified_count = sum(
        1
        for r in reports
        if bool(r.photo_url)
        or (r.verification is not None and r.verification.status in VALID_STATUSES)
    )
    score = verified_count / len(reports)
    evidence = (
        [
            f"Доля подтверждённых обращений: {verified_count}/{len(reports)} ({score:.0%})"
        ]
        if score > 0
        else []
    )
    return (round(score, 4), evidence)
