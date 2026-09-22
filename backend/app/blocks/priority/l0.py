"""L0: базовый уровень объяснимого приоритета кластера на чистой математике."""

from app.contracts.models import Cluster, Context, Factor, Priority, Report

from . import factors

FACTORS = [
    ("HZ", "Опасность", 0.25, factors.hz),
    ("DM", "Спрос", 0.15, factors.dm),
    ("AG", "Возраст", 0.15, factors.ag),
    ("SP", "Соц. объекты", 0.15, factors.sp),
    ("RC", "Повтор", 0.10, factors.rc),
    ("EX", "Мероприятие", 0.10, factors.ex),
    ("WX", "Погода", 0.05, factors.wx),
    ("VF", "Достоверность", 0.05, factors.vf),
]


def score(
    cluster: Cluster,
    reports: list[Report],
    history: list[Report],
    ctx: Context,
    weights: dict[str, float] | None = None,
) -> Priority:
    """Вычисляет приоритет кластера по формуле взвешенной суммы с перенормировкой и аварийным минимумом."""
    w_map = {
        c: (weights.get(c, w) if weights and c in weights and weights[c] >= 0 else w)
        for c, _, w, _ in FACTORS
    }
    tot_w = sum(w_map.values())
    res = [
        (c, lbl, *mod.evaluate(cluster, reports, history, ctx), w_map[c])
        for c, lbl, _, mod in FACTORS
    ]
    val_w = sum(w for _, _, s, _, w in res if s is not None)
    conf = min(1.0, max(0.0, val_w / tot_w)) if tot_w > 0 else 0.0
    raw = (
        (100.0 * sum(w * s for _, _, s, _, w in res if s is not None) / val_w)
        if val_w > 0
        else 0.0
    )
    raw = max(0.0, min(100.0, raw))

    items = [
        Factor(
            code=c,
            label=lbl,
            score=s,
            weight=w,
            points=(
                round(100.0 * (w * s) / val_w, 2)
                if (s is not None and val_w > 0)
                else 0.0
            ),
            evidence=ev,
        )
        for c, lbl, s, ev, w in res
    ]

    final = raw
    hz = next((r for r in res if r[0] == "HZ"), None)
    if hz and hz[2] is not None and hz[2] >= 0.9 and raw < 80.0:
        diff = 80.0 - raw
        final = 80.0
        items.append(
            Factor(
                code="FL",
                label="Аварийный минимум",
                score=1.0,
                weight=0.0,
                points=round(diff, 2),
                evidence=[
                    f"Опасность категории (HZ={hz[2]:.1f} ≥ 0.9) активировала аварийный минимум 80 баллов (+{diff:.1f})"
                ],
            )
        )

    suspicious = any(
        r.verification and r.verification.status == "suspicious" for r in reports
    )
    return Priority(
        cluster_id=cluster.id,
        score=round(final, 1),
        factors=items,
        confidence=round(conf, 2),
        needs_review=(conf < 0.5) or suspicious,
    )
