"""L1: целевой уровень объяснимого приоритета кластера со всеми факторами и весами из YAML."""

from pathlib import Path

import yaml  # type: ignore[import-untyped]

from app.contracts.models import Cluster, Context, Factor, Priority, Report

from . import factors

WEIGHTS_PATH = Path(__file__).resolve().parent / "weights.yaml"
DEFAULT_WEIGHTS: dict[str, float] = {
    "HZ": 0.25,
    "DM": 0.15,
    "AG": 0.15,
    "SP": 0.15,
    "RC": 0.10,
    "WX": 0.05,
    "VF": 0.05,
    "EX": 0.10,
}

FACTOR_DEFS = [
    ("HZ", "Опасность", factors.hz),
    ("DM", "Спрос", factors.dm),
    ("AG", "Возраст", factors.ag),
    ("SP", "Соц. объекты", factors.sp),
    ("RC", "Повтор", factors.rc),
    ("EX", "Мероприятие", factors.ex),
    ("WX", "Погода", factors.wx),
    ("VF", "Достоверность", factors.vf),
]


def load_weights() -> dict[str, float]:
    """Загружает веса из weights.yaml с fallback на значения по умолчанию."""
    w = DEFAULT_WEIGHTS.copy()
    if WEIGHTS_PATH.is_file():
        try:
            data = yaml.safe_load(WEIGHTS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if k in w and isinstance(v, (int, float)) and v >= 0:
                        w[k] = float(v)
        except Exception:
            pass
    return w


def score(
    cluster: Cluster,
    reports: list[Report],
    history: list[Report],
    ctx: Context,
    weights: dict[str, float] | None = None,
) -> Priority:
    """Вычисляет приоритет уровня L1 по всем факторам с весами из weights.yaml."""
    w_map = load_weights()
    if weights:
        for k, v in weights.items():
            if k in w_map and v >= 0:
                w_map[k] = v

    total_weight = sum(w_map.values())
    res = [
        (
            c,
            lbl,
            *mod.evaluate(cluster, reports, history, ctx),
            w_map.get(c, 0.0),
        )
        for c, lbl, mod in FACTOR_DEFS
    ]
    valid_weight = sum(w for _, _, s, _, w in res if s is not None)
    conf = min(1.0, max(0.0, valid_weight / total_weight)) if total_weight > 0 else 0.0
    raw = (
        (100.0 * sum(w * s for _, _, s, _, w in res if s is not None) / valid_weight)
        if valid_weight > 0
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
                round(100.0 * (w * s) / valid_weight, 2)
                if (s is not None and valid_weight > 0)
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
