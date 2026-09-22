"""Блок B3 · Дубликаты → кластеры. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B3_clusters.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from collections.abc import Callable

from app.contracts.models import Cluster, Report

SimilarityFn = Callable[[str, str], float]  # 0..1

DUP_SURE_RADIUS_M = 50
DUP_RADIUS_M = 100
DUP_TEXT_SIM = 0.5
DUP_WINDOW_DAYS = 30


def build_clusters(
    reports: list[Report], similarity: SimilarityFn | None = None
) -> list[Cluster]:
    raise NotImplementedError("B3: реализуй по контракту docs/contracts/B3_clusters.md")
