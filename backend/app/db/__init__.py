"""Блок D1 · База данных и репозиторий. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/D1_db.md. Реализация: l0.py (без сети, L0), l1.py (целевой уровень).
"""

import logging
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
from app.core.config import settings

from . import l0, l1

log = logging.getLogger(__name__)


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
    """Единая точка входа. Уровень выбирается переключателем USE_MOCK."""
    if settings.USE_MOCK:
        return l0.repo
    try:
        return l1.repo
    except Exception:  # noqa: BLE001 — любая ошибка L1 = тихий откат на L0, не падение
        log.warning("D1: L1 failed, falling back to L0", exc_info=True)
        return l0.repo
