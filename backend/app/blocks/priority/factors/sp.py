"""Фактор SP: Социальные объекты (вес 0.15).

school/kindergarten/hospital:
<= 150 м -> 1.0;
<= 300 м -> 0.5;
иначе -> 0.
Нет инфраструктуры в ctx -> None.
"""

from app.contracts.models import Cluster, Context, Report

from ..geo_utils import haversine_m

SOCIAL_KINDS = {"school", "kindergarten", "hospital"}


def evaluate(
    cluster: Cluster, reports: list[Report], history: list[Report], ctx: Context
) -> tuple[float | None, list[str]]:
    _ = (reports, history)
    if not ctx.infrastructure:
        return (None, [])

    social_objs = [obj for obj in ctx.infrastructure if obj.kind in SOCIAL_KINDS]
    if not social_objs:
        return (0.0, [])

    nearest_obj, min_d = None, float("inf")
    for obj in social_objs:
        d = haversine_m(cluster.centroid, obj.location)
        if d < min_d:
            min_d = d
            nearest_obj = obj

    if min_d <= 150.0:
        score = 1.0
    elif min_d <= 300.0:
        score = 0.5
    else:
        score = 0.0

    evidence: list[str] = []
    if score > 0 and nearest_obj:
        evidence.append(
            f"Соц. объект '{nearest_obj.name}' ({nearest_obj.kind}) в {min_d:.0f} м (≤ {150 if score == 1.0 else 300} м)"
        )
    return (score, evidence)
