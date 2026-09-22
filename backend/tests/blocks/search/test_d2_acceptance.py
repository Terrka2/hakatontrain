"""Тесты критериев приёмки D2 · уровень L0/L1.

Запуск: cd backend && uv run pytest tests/blocks/search/test_d2_acceptance.py -q

Все тесты сейчас красные — реализация ещё не создана.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.blocks import search
from app.blocks.search import Hit, text_similarity
from app.contracts.models import Event, Report
from app.core.config import settings

FIXTURE = Path(__file__).resolve().parents[3] / "app" / "fixtures" / "demo_city.json"


@pytest.fixture(scope="module")
def data() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def reports(data: dict[str, Any]) -> dict[str, Report]:
    return {r["id"]: Report(**r) for r in data["reports"]}


@pytest.fixture(scope="module")
def events(data: dict[str, Any]) -> dict[str, Event]:
    return {e["id"]: Event(**e) for e in data["events"]}


# ---------------------------------------------------------------------------
# Критерий 1: text_similarity кросс-языковая — RU↔RO одна яма > RU разные темы
# ---------------------------------------------------------------------------


def test_text_similarity_cross_language(
    reports: dict[str, Report],
) -> None:
    """Критерий 1 (L0 tfidf): text_similarity(r001, r002) > text_similarity(r001, r005)."""
    r001 = reports["r001"]
    r002 = reports["r002"]
    r005 = reports["r005"]

    sim_same_topic = text_similarity(r001.text, r002.text)  # RU↔RO, одна яма
    sim_diff_topic = text_similarity(r001.text, r005.text)  # RU яма vs скамейка

    assert isinstance(sim_same_topic, float), "text_similarity должна возвращать float"
    assert isinstance(sim_diff_topic, float), "text_similarity должна возвращать float"
    assert 0.0 <= sim_same_topic <= 1.0, f"sim_same_topic={sim_same_topic} вне [0, 1]"
    assert 0.0 <= sim_diff_topic <= 1.0, f"sim_diff_topic={sim_diff_topic} вне [0, 1]"
    assert sim_same_topic > sim_diff_topic, (
        f"Ожидалось sim(r001,r002)={sim_same_topic:.3f} > sim(r001,r005)={sim_diff_topic:.3f}, "
        "но одна яма не оказалась ближе разной темы"
    )


# ---------------------------------------------------------------------------
# Критерий 2: search("яма у школы") → r001 или r003 в топ-3
# ---------------------------------------------------------------------------


def test_search_returns_relevant_reports() -> None:
    """Критерий 2: поиск 'яма у школы' возвращает r001 или r003 в топ-3."""
    results: list[Hit] = search.search("яма у школы", k=3)

    assert len(results) <= 3, f"search вернул {len(results)} результатов вместо ≤ 3"
    result_ids = [h.id for h in results]
    assert "r001" in result_ids or "r003" in result_ids, (
        f"Ни r001, ни r003 не найдены в топ-3: {result_ids}"
    )
    for hit in results:
        assert hit.kind in ("report", "event")
        assert 0.0 <= hit.score <= 1.0
        assert isinstance(hit.snippet, str)


# ---------------------------------------------------------------------------
# Критерий 3: search("забег") → событие e1
# ---------------------------------------------------------------------------


def test_search_returns_event() -> None:
    """Критерий 3: поиск 'забег' возвращает событие e1."""
    results: list[Hit] = search.search("забег", k=5)

    result_ids = [h.id for h in results]
    assert "e1" in result_ids, (
        f"Событие e1 ('Chișinău Sprint — городской забег') не найдено в топ-5: {result_ids}"
    )
    e1_hit = next(h for h in results if h.id == "e1")
    assert e1_hit.kind == "event"


# ---------------------------------------------------------------------------
# Критерий 4: откат на L0 при ошибке L1
# ---------------------------------------------------------------------------


def test_fallback_to_l0_on_l1_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Критерий 4: ошибка L1 → откат на tfidf без исключения (с warning в лог)."""
    monkeypatch.setattr(settings, "EMBEDDER", "st")

    # Ломаем L1 — text_similarity кидает RuntimeError
    from app.blocks.search import l1 as search_l1

    def broken_text_similarity(_a: str, _b: str) -> float:
        raise RuntimeError("L1 model not available (test)")

    monkeypatch.setattr(search_l1, "text_similarity", broken_text_similarity)

    result = text_similarity("тест", "тест")

    assert isinstance(result, float), f"Ожидался float, получено {type(result)}"
    assert 0.0 <= result <= 1.0, f"Результат {result} вне диапазона [0, 1]"

