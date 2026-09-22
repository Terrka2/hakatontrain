"""Блок D1 · База данных и репозиторий. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/D1_db.md. Реализация: l0.py (заглушка/L0), l1.py (целевой уровень).
"""

import os
from datetime import datetime
from typing import Protocol

from app.contracts.models import (
    Cluster,
    Crew,
    Event,
    InfraObject,
    OperatorRun,
    Plan,
    Priority,
    Report,
)


class Repository(Protocol):
    """Интерфейс описан в контракте D1. Остальные блоки работают только через него."""

    def list_reports(
        self, *, status: str | None = None, category: str | None = None
    ) -> list[Report]: ...
    def upsert_reports(self, reports: list[Report]) -> int: ...
    def confirm_report(self, report_id: str) -> Report: ...
    def save_clusters(
        self, clusters: list[Cluster], priorities: dict[str, Priority]
    ) -> None: ...
    def list_clusters(self) -> list[tuple[Cluster, Priority | None]]: ...
    def list_events(self, start: datetime, end: datetime) -> list[Event]: ...
    def add_event(self, event: Event) -> Event: ...
    def list_infrastructure(self) -> list[InfraObject]: ...
    def list_crews(self) -> list[Crew]: ...
    def save_plan(self, plan: Plan) -> None: ...
    def get_plan(self, plan_id: str) -> Plan | None: ...
    def current_plan(
        self, status: str = "approved"
    ) -> Plan | None: ...  # последний с таким статусом
    def set_stop_status(self, plan_id: str, job_id: str, status: str) -> None: ...
    def add_run(self, run: OperatorRun) -> None: ...
    def list_runs(self, limit: int = 20) -> list[OperatorRun]: ...
    def set_needs_review(self, cluster_id: str, value: bool, reason: str) -> None: ...
    def reset(self) -> None: ...  # вернуть состояние к fixture


def get_repository() -> Repository:
    """Возвращает репозиторий согласно настройке USE_MOCK (по умолчанию L0/MemoryRepository)."""
    use_mock_str = os.getenv("USE_MOCK", "true").lower()
    use_mock = use_mock_str in ("true", "1", "yes")
    if use_mock:
        from app.db.l0 import MemoryRepository

        return MemoryRepository()
    raise NotImplementedError("D1: L1 SqlRepository еще не реализован")
