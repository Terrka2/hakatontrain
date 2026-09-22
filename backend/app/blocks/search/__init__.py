"""Блок D2 · Эмбеддинги и семантический поиск (RAG). Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/D2_search.md. Реализация: l0.py (tfidf), l1.py (sentence-transformers).
"""

import logging

from app.core.config import settings

from . import l0, l1
from .models import Hit

log = logging.getLogger(__name__)

__all__ = ["Hit", "embed", "search", "text_similarity"]


def embed(texts: list[str]) -> list[list[float]]:
    """Единая точка входа. Уровень выбирается переключателем EMBEDDER."""
    if settings.EMBEDDER == "tfidf":
        return l0.embed(texts)
    try:
        return l1.embed(texts)
    except Exception:  # noqa: BLE001
        log.warning("D2: L1 embed failed, falling back to L0", exc_info=True)
        return l0.embed(texts)


def text_similarity(a: str, b: str) -> float:
    """Схожесть двух текстов [0, 1]. Передаётся в B3 для дедупликации."""
    if settings.EMBEDDER == "tfidf":
        return l0.text_similarity(a, b)
    try:
        return l1.text_similarity(a, b)
    except Exception:  # noqa: BLE001
        log.warning("D2: L1 text_similarity failed, falling back to L0", exc_info=True)
        return l0.text_similarity(a, b)


def search(query: str, k: int = 5, kind: str | None = None) -> list[Hit]:
    """Семантический поиск по обращениям и событиям."""
    if settings.EMBEDDER == "tfidf":
        return l0.search(query, k=k, kind=kind)
    try:
        return l1.search(query, k=k, kind=kind)
    except Exception:  # noqa: BLE001
        log.warning("D2: L1 search failed, falling back to L0", exc_info=True)
        return l0.search(query, k=k, kind=kind)
