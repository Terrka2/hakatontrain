"""ЕДИНСТВЕННОЕ место, где вызывается LLM-провайдер. Владелец: блок L1 (Некит)."""

from pydantic import BaseModel


def complete_json(
    system: str, user: str, schema: type[BaseModel], *, timeout_s: float = 8
) -> BaseModel | None:
    raise NotImplementedError(
        "L1: реализуй по контракту docs/contracts/L1_extractor.md"
    )
