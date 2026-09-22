"""Уровень L0 блока D1: MemoryRepository на основе демо-фикстуры demo_city.json."""

import json
from datetime import datetime
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

    def list_reports(
        self, *, status: str | None = None, category: str | None = None
    ) -> list[Report]:
        reports = list(self._reports.values())
        if status is not None:
            reports = [r for r in reports if r.status == status]
        if category is not None:
            reports = [r for r in reports if r.category == category]
        return reports

    def upsert_reports(self, reports: list[Report]) -> int:
        count = 0
        for report in reports:
            self._reports[report.id] = report
            count += 1
        return count

    def confirm_report(self, report_id: str) -> Report:
        if report_id not in self._reports:
            raise KeyError(f"Report {report_id} not found")
        report = self._reports[report_id]
        updated = report.model_copy(update={"confirmations": report.confirmations + 1})
        self._reports[report_id] = updated
        return updated

    def save_clusters(
        self, clusters: list[Cluster], priorities: dict[str, Priority]
    ) -> None:
        for cluster in clusters:
            self._clusters[cluster.id] = cluster
        for cluster_id, priority in priorities.items():
            self._priorities[cluster_id] = priority

    def list_clusters(self) -> list[tuple[Cluster, Priority | None]]:
        res: list[tuple[Cluster, Priority | None]] = []
        for cluster in self._clusters.values():
            res.append((cluster, self._priorities.get(cluster.id)))
        return res

    def list_events(self, start: datetime, end: datetime) -> list[Event]:
        return [
            e
            for e in self._events
            if start <= e.starts_at <= end or start <= e.ends_at <= end
        ]

    def add_event(self, event: Event) -> Event:
        self._events.append(event)
        return event

    def list_infrastructure(self) -> list[InfraObject]:
        return list(self._infrastructure)

    def list_crews(self) -> list[Crew]:
        return list(self._crews)

    def save_plan(self, plan: Plan) -> None:
        self._plans[plan.id] = plan

    def get_plan(self, plan_id: str) -> Plan | None:
        return self._plans.get(plan_id)

    def current_plan(self, status: str = "approved") -> Plan | None:
        matching = [p for p in self._plans.values() if p.status == status]
        return matching[-1] if matching else None

    def set_stop_status(self, plan_id: str, job_id: str, status: str) -> None:
        plan = self._plans.get(plan_id)
        if not plan:
            return
        for route in plan.routes:
            for stop in route.stops:
                if stop.job_id == job_id:
                    stop.status = status

    def add_run(self, run: OperatorRun) -> None:
        self._runs.append(run)

    def list_runs(self, limit: int = 20) -> list[OperatorRun]:
        return list(reversed(self._runs[-limit:]))

    def set_needs_review(self, cluster_id: str, value: bool, reason: str) -> None:
        if cluster_id in self._priorities:
            self._priorities[cluster_id].needs_review = value


# Синглтон уровня модуля L0 для сохранения состояния между вызовами get_repository()
repo = MemoryRepository()
