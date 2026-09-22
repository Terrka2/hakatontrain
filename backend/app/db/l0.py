"""Уровень L0 блока D1: MemoryRepository на основе демо-фикстуры demo_city.json."""

import json
from datetime import UTC, datetime
from pathlib import Path

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

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "demo_city.json"


class MemoryRepository:
    """Реализация репозитория в памяти (L0)."""

    def __init__(self) -> None:
        self._reports: dict[str, Report] = {}
        self._clusters: dict[str, Cluster] = {}
        self._priorities: dict[str, Priority] = {}
        self._events: list[Event] = []
        self._infrastructure: list[InfraObject] = []
        self._crews: list[Crew] = []
        self._plans: dict[str, Plan] = {}
        self._runs: list[OperatorRun] = []
        self._needs_review_reasons: dict[str, str] = {}
        self.reset()

    def reset(self) -> None:
        """Вернуть состояние к fixture."""
        with open(FIXTURE_PATH, encoding="utf-8") as f:
            data = json.load(f)

        self._reports = {r["id"]: Report(**r) for r in data.get("reports", [])}
        self._clusters = {c["id"]: Cluster(**c) for c in data.get("clusters", [])}
        self._priorities = {
            p["cluster_id"]: Priority(**p) for p in data.get("priorities", [])
        }
        self._events = [Event(**e) for e in data.get("events", [])]
        self._infrastructure = [
            InfraObject(**i) for i in data.get("infrastructure", [])
        ]
        self._crews = [Crew(**c) for c in data.get("crews", [])]
        self._plans = {}
        self._runs = []
        self._needs_review_reasons = {}

    def list_reports(
        self, *, status: str | None = None, category: str | None = None
    ) -> list[Report]:
        reports = list(self._reports.values())
        if status is not None:
            reports = [r for r in reports if r.status == status]
        if category is not None:
            reports = [r for r in reports if r.category == category]
        return [r.model_copy(deep=True) for r in reports]

    def upsert_reports(self, reports: list[Report]) -> int:
        count = 0
        for report in reports:
            if report.id in self._reports:
                existing = self._reports[report.id]
                updated_cluster_id = (
                    report.cluster_id
                    if report.cluster_id is not None
                    else existing.cluster_id
                )
                updated_extracted = (
                    report.extracted
                    if report.extracted is not None
                    else existing.extracted
                )
                updated_verification = (
                    report.verification
                    if report.verification is not None
                    else existing.verification
                )
                merged = report.model_copy(
                    deep=True,
                    update={
                        "cluster_id": updated_cluster_id,
                        "extracted": (
                            updated_extracted.model_copy(deep=True)
                            if updated_extracted is not None
                            else None
                        ),
                        "verification": (
                            updated_verification.model_copy(deep=True)
                            if updated_verification is not None
                            else None
                        ),
                    },
                )
                self._reports[report.id] = merged
            else:
                self._reports[report.id] = report.model_copy(deep=True)
            count += 1
        return count

    def confirm_report(self, report_id: str) -> Report:
        if report_id not in self._reports:
            raise KeyError(f"Report {report_id} not found")
        report = self._reports[report_id]
        updated = report.model_copy(update={"confirmations": report.confirmations + 1})
        self._reports[report_id] = updated
        return updated.model_copy(deep=True)

    def save_clusters(
        self, clusters: list[Cluster], priorities: dict[str, Priority]
    ) -> None:
        for cluster in clusters:
            self._clusters[cluster.id] = cluster.model_copy(deep=True)
        for cluster_id, priority in priorities.items():
            self._priorities[cluster_id] = priority.model_copy(deep=True)

    def list_clusters(self) -> list[tuple[Cluster, Priority | None]]:
        res: list[tuple[Cluster, Priority | None]] = []
        for cluster in self._clusters.values():
            p = self._priorities.get(cluster.id)
            res.append(
                (
                    cluster.model_copy(deep=True),
                    p.model_copy(deep=True) if p is not None else None,
                )
            )
        return res

    def list_events(self, start: datetime, end: datetime) -> list[Event]:
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)

        res: list[Event] = []
        for e in self._events:
            e_start = (
                e.starts_at
                if e.starts_at.tzinfo is not None
                else e.starts_at.replace(tzinfo=UTC)
            )
            e_end = (
                e.ends_at
                if e.ends_at.tzinfo is not None
                else e.ends_at.replace(tzinfo=UTC)
            )
            if e_start <= end and e_end >= start:
                res.append(e.model_copy(deep=True))
        return res

    def add_event(self, event: Event) -> Event:
        stored = event.model_copy(deep=True)
        self._events.append(stored)
        return stored.model_copy(deep=True)

    def list_infrastructure(self) -> list[InfraObject]:
        return [i.model_copy(deep=True) for i in self._infrastructure]

    def list_crews(self) -> list[Crew]:
        return [c.model_copy(deep=True) for c in self._crews]

    def save_plan(self, plan: Plan) -> None:
        self._plans[plan.id] = plan.model_copy(deep=True)

    def get_plan(self, plan_id: str) -> Plan | None:
        plan = self._plans.get(plan_id)
        return plan.model_copy(deep=True) if plan is not None else None

    def current_plan(self, status: str = "approved") -> Plan | None:
        matching = [p for p in self._plans.values() if p.status == status]
        if not matching:
            return None
        matching.sort(key=lambda p: p.version, reverse=True)
        return matching[0].model_copy(deep=True)

    def set_stop_status(self, plan_id: str, job_id: str, status: str) -> None:
        plan = self._plans.get(plan_id)
        if not plan:
            return
        for route in plan.routes:
            for stop in route.stops:
                if stop.job_id == job_id:
                    stop.status = status

    def add_run(self, run: OperatorRun) -> None:
        self._runs.append(run.model_copy(deep=True))

    def list_runs(self, limit: int = 20) -> list[OperatorRun]:
        if limit <= 0:
            return []
        runs = self._runs[-limit:]
        return [r.model_copy(deep=True) for r in reversed(runs)]

    def set_needs_review(self, cluster_id: str, value: bool, reason: str) -> None:
        if cluster_id not in self._clusters:
            raise ValueError(f"Cluster with id '{cluster_id}' does not exist")
        self._needs_review_reasons[cluster_id] = reason
        if cluster_id in self._priorities:
            self._priorities[cluster_id] = self._priorities[cluster_id].model_copy(
                update={"needs_review": value}
            )


# Синглтон уровня модуля L0 для сохранения состояния между вызовами get_repository()
repo = MemoryRepository()
