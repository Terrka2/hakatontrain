"""Блок L2 · LLM: ассистент-диспетчер на фиксированном графе. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/L2_assistant.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from typing import Literal

from app.contracts.models import AssistantRequest, AssistantResponse, OperatorRun

Intent = Literal[
    "what_happened",
    "explain_priority",
    "explain_plan",
    "find_similar",
    "crew_status",
    "rebuild_plan",
    "set_weather",
    "review_cluster",
    "approve_plan",
    "my_route",
    "report_job",
    "smalltalk",
    "unknown",
]


def handle(req: AssistantRequest) -> AssistantResponse:
    raise NotImplementedError(
        "L2: реализуй по контракту docs/contracts/L2_assistant.md"
    )


def confirm(session_id: str, pending_id: str, approve: bool) -> AssistantResponse:
    raise NotImplementedError(
        "L2: реализуй по контракту docs/contracts/L2_assistant.md"
    )


def narrate(run: OperatorRun) -> str:
    raise NotImplementedError(
        "L2: реализуй по контракту docs/contracts/L2_assistant.md"
    )
