"""Уровень L0 блока D1: MemoryRepository на основе демо-фикстуры demo_city.json."""

from datetime import datetime

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


class MemoryRepository:
    """Реализация репозитория в памяти (L0)."""

    def list_reports(
        self, *, status: str | None = None, category: str | None = None
    ) -> list[Report]:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def upsert_reports(self, reports: list[Report]) -> int:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def confirm_report(self, report_id: str) -> Report:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def save_clusters(
        self, clusters: list[Cluster], priorities: dict[str, Priority]
    ) -> None:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def list_clusters(self) -> list[tuple[Cluster, Priority | None]]:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def list_events(self, start: datetime, end: datetime) -> list[Event]:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def add_event(self, event: Event) -> Event:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def list_infrastructure(self) -> list[InfraObject]:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def list_crews(self) -> list[Crew]:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def save_plan(self, plan: Plan) -> None:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def get_plan(self, plan_id: str) -> Plan | None:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def current_plan(self, status: str = "approved") -> Plan | None:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def set_stop_status(self, plan_id: str, job_id: str, status: str) -> None:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def add_run(self, run: OperatorRun) -> None:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def list_runs(self, limit: int = 20) -> list[OperatorRun]:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def set_needs_review(self, cluster_id: str, value: bool, reason: str) -> None:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )

    def reset(self) -> None:
        raise NotImplementedError(
            "MemoryRepository: реализуй по контракту docs/contracts/D1_db.md"
        )
