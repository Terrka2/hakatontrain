"""Фактор HZ: Опасность (вес 0.25). Базовая опасность + 0.2 за сигналы/травмы."""

import re

from app.contracts.models import Cluster, Context, Report

BASE: dict[str, float] = {
    "manhole": 0.9,
    "tree": 0.7,
    "water_leak": 0.6,
    "pothole": 0.5,
    "traffic_sign": 0.5,
    "streetlight": 0.4,
    "garbage": 0.2,
    "public_space": 0.1,
}
SIG_RE = re.compile(
    r"(упал|реб[её]нок|дет[исад]|травм|дтп|авари|пострада|люк|нет крышки|опасн|угроз|скорая|"
    r"copi|accident|r[aă]nit|c[aă]zut|pericol|urgen|fall|fell|child|injur|danger|hazard)",
    re.IGNORECASE,
)


def evaluate(
    cluster: Cluster, reports: list[Report], history: list[Report], ctx: Context
) -> tuple[float | None, list[str]]:
    _ = (history, ctx)
    base = BASE.get(cluster.category.lower(), 0.1)
    has_sig, reason = False, None
    for r in reports:
        if r.extracted and r.extracted.injured:
            has_sig, reason = True, "Зафиксированы пострадавшие (extracted.injured)"
            break
        if r.extracted and r.extracted.hazard_signals:
            has_sig = True
            reason = f"Сигналы опасности: {', '.join(r.extracted.hazard_signals)}"
            break
        if r.text and SIG_RE.search(r.text):
            has_sig = True
            reason = "Слова-сигналы опасности в тексте обращения"
            break

    score = min(1.0, max(0.0, base + (0.2 if has_sig else 0.0)))
    evidence = [f"Категория '{cluster.category}': базовая опасность {base:.1f}"]
    if has_sig and reason:
        evidence.append(f"{reason} (+0.2)")
    return (round(score, 4), evidence)
