"""Блок L3 · Инструменты оператора и MCP-сервер. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/L3_tools.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from pydantic import BaseModel

from app.contracts.models import PendingAction


class Tool(BaseModel):
    name: str
    description: str
    args_schema: type[BaseModel]
    writes: bool
    requires_human: bool  # True → только PendingAction, выполняет человек-supervisor
    roles: list[str]  # supervisor | crew


REGISTRY: dict[str, Tool] = {}


def call(
    name: str, args: dict[str, object], role: str, actor: str
) -> BaseModel | PendingAction:
    raise NotImplementedError("L3: реализуй по контракту docs/contracts/L3_tools.md")


def execute_pending(action: PendingAction, role: str, actor: str) -> BaseModel:
    raise NotImplementedError("L3: реализуй по контракту docs/contracts/L3_tools.md")
