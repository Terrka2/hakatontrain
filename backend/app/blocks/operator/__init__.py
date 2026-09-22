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


class PipelineResult(BaseModel):
    clusters: list[Cluster]
    priorities: dict[str, Priority]  # cluster_id -> Priority
    context: Context


def run_pipeline(reports: list[Report], now: datetime) -> PipelineResult:
    raise NotImplementedError("B0: реализуй по контракту docs/contracts/B0_operator.md")


def operator_run(
    trigger: str, now: datetime, job_update: JobUpdate | None = None
) -> OperatorRun:
    raise NotImplementedError("B0: реализуй по контракту docs/contracts/B0_operator.md")
