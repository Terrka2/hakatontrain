"""Блок B0 · ИИ-оператор: самостоятельный проход. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B0_operator.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from datetime import datetime

from pydantic import BaseModel

from app.contracts.models import (
    Cluster,
    Context,
    JobUpdate,
    OperatorRun,
    Priority,
    Report,
)

from . import l0
from .l0 import get_cluster, get_clusters, get_plan, get_runs, review_cluster

__all__ = [
    "PipelineResult",
    "run_pipeline",
    "operator_run",
    "get_cluster",
    "get_clusters",
    "get_plan",
    "get_runs",
    "review_cluster",
]


class PipelineResult(BaseModel):
    clusters: list[Cluster]
    priorities: dict[str, Priority]  # cluster_id -> Priority
    context: Context


def run_pipeline(reports: list[Report], now: datetime) -> PipelineResult:
    return l0.run_pipeline(reports, now)


def operator_run(
    trigger: str, now: datetime, job_update: JobUpdate | None = None
) -> OperatorRun:
    return l0.operator_run(trigger, now, job_update)
