"""Блок D2 · Эмбеддинги и семантический поиск (RAG). Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/D2_search.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from typing import Literal

from pydantic import BaseModel


class Hit(BaseModel):
    kind: Literal["report", "event"]
    id: str
    score: float
    snippet: str


def embed(texts: list[str]) -> list[list[float]]:
    raise NotImplementedError("D2: реализуй по контракту docs/contracts/D2_search.md")


def text_similarity(a: str, b: str) -> float:
    raise NotImplementedError("D2: реализуй по контракту docs/contracts/D2_search.md")


def search(query: str, k: int = 5, kind: str | None = None) -> list[Hit]:
    raise NotImplementedError("D2: реализуй по контракту docs/contracts/D2_search.md")
