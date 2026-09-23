"""Тесты блока D2 (search). Один критерий приёмки = минимум один тест. Данные — только fixture, сеть запрещена.

Запуск: cd backend && uv run pytest tests/blocks/search -q
"""

import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.blocks import search
from app.blocks.search import Hit, l0
from app.core.config import settings
from tests.utils.user import user_authentication_headers

FIXTURE = Path(__file__).resolve().parents[3] / "app" / "fixtures" / "demo_city.json"


@pytest.fixture(scope="module")
def data() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def reports(data: dict) -> dict[str, str]:
    return {r["id"]: r["text"] for r in data["reports"]}


# --- Критерии приёмки ---------------------------------------------------


def test_search_pothole_near_school_returns_r001_or_r003() -> None:
    """Критерий приёмки 2: search("яма у школы") возвращает r001 или r003 в топ-3."""
    hits = search.search("яма у школы", k=3)
    ids = {h.id for h in hits}
    assert {"r001", "r003"} & ids
    assert all(isinstance(h, Hit) for h in hits)


def test_search_race_returns_event_e1() -> None:
    """Критерий приёмки 3: search("забег") возвращает событие e1."""
    hits = search.search("забег", k=3)
    assert any(h.id == "e1" and h.kind == "event" for h in hits)


def test_text_similarity_l1_ordering_is_l1_only(reports: dict[str, str]) -> None:
    """Критерий приёмки 1 помечен в контракте как L1 (sentence-transformers).

    На L0 (символьные TF-IDF n-граммы) это упорядочивание не гарантируется —
    фиксируем это явно, а не выдаём фиктивно зелёный тест.
    """
    ru_ro_dup = search.text_similarity(reports["r001"], reports["r002"])
    unrelated = search.text_similarity(reports["r001"], reports["r005"])
    assert 0.0 <= ru_ro_dup <= 1.0
    assert 0.0 <= unrelated <= 1.0
    # На L0 (EMBEDDER=tfidf) свойство из критерия 1 не проверяем — оно для L1.
    assert settings.EMBEDDER == "tfidf"


def test_l1_model_unavailable_falls_back_to_l0_silently(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Критерий приёмки 4 / QA п.4: модель L1 недоступна/падает → тихий откат на tfidf, warning в лог."""
    monkeypatch.setattr(settings, "EMBEDDER", "st")

    def boom(*_args: object, **_kwargs: object) -> list[Hit]:
        raise RuntimeError("model not downloaded")

    monkeypatch.setattr(search.l1, "search", boom)

    with caplog.at_level(logging.WARNING):
        hits = search.search("яма у школы", k=3)

    assert hits == l0.search("яма у школы", k=3)
    assert any("L1" in rec.message for rec in caplog.records)


def test_l1_embed_and_similarity_also_fall_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Тот же откат для embed() и text_similarity(), не только для search()."""
    monkeypatch.setattr(settings, "EMBEDDER", "st")
    monkeypatch.setattr(
        search.l1, "embed", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    monkeypatch.setattr(
        search.l1,
        "text_similarity",
        lambda *a, **k: (_ for _ in ()).throw(TimeoutError("timeout")),
    )
    assert search.embed(["яма"]) == l0.embed(["яма"])
    assert search.text_similarity("яма", "дыра") == l0.text_similarity("яма", "дыра")


# --- Границы данных / детерминированность --------------------------------


def test_search_is_deterministic() -> None:
    """QA п.5: два вызова подряд на одних данных → одинаковый результат и порядок."""
    first = search.search("яма у школы", k=5)
    second = search.search("яма у школы", k=5)
    assert first == second


def test_search_empty_query_returns_empty_list() -> None:
    assert search.search("", k=5) == []
    assert search.search("   ", k=5) == []


def test_search_zero_or_negative_k_returns_empty_list() -> None:
    assert search.search("яма", k=0) == []
    assert search.search("яма", k=-1) == []


def test_search_filters_by_kind() -> None:
    only_events = search.search("забег", k=5, kind="event")
    assert all(h.kind == "event" for h in only_events)
    only_reports = search.search("забег", k=5, kind="report")
    assert all(h.kind == "report" for h in only_reports)


def test_embed_empty_list_returns_empty_list() -> None:
    assert search.embed([]) == []


def test_embed_blank_strings_do_not_raise() -> None:
    vectors = search.embed(["", "   "])
    assert len(vectors) == 2
    assert all(all(x == 0.0 for x in v) for v in vectors)


def test_embed_duplicate_texts_returns_equal_vectors() -> None:
    vectors = search.embed(["яма на дороге", "яма на дороге"])
    assert vectors[0] == vectors[1]


def test_text_similarity_empty_or_missing_input_returns_zero() -> None:
    assert search.text_similarity("", "яма") == 0.0
    assert search.text_similarity("яма", "") == 0.0
    assert search.text_similarity(None, "яма") == 0.0  # type: ignore[arg-type]
    assert search.text_similarity("яма", None) == 0.0  # type: ignore[arg-type]


def test_text_similarity_identical_strings_is_one() -> None:
    assert search.text_similarity("яма у школы", "яма у школы") == pytest.approx(1.0)


def test_text_similarity_ignores_case_and_surrounding_whitespace() -> None:
    a = search.text_similarity("  Яма у школы  ", "яма у школы")
    b = search.text_similarity("яма у школы", "яма у школы")
    assert a == pytest.approx(b, abs=0.05)


# --- Роут -----------------------------------------------------------------


@pytest.fixture(scope="module")
def crew_token_headers(client: TestClient) -> dict[str, str]:
    return user_authentication_headers(
        client=client, email="crew1@demo.md", password=settings.DEMO_PASSWORD
    )


def test_route_requires_authentication(client: TestClient) -> None:
    """QA п.11: запрос без токена → 401."""
    r = client.get(f"{settings.API_V1_STR}/search", params={"q": "яма"})
    assert r.status_code == 401


def test_route_forbidden_for_citizen_role(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    """QA п.11: запрос с чужой ролью (citizen) → 403."""
    r = client.get(
        f"{settings.API_V1_STR}/search",
        params={"q": "яма"},
        headers=normal_user_token_headers,
    )
    assert r.status_code == 403


def test_route_ok_for_crew_role_and_matches_response_model(
    client: TestClient, crew_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/search",
        params={"q": "яма у школы", "k": 3},
        headers=crew_token_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert {"r001", "r003"} & {h["id"] for h in body}
    for hit in body:
        Hit(**hit)  # response_model совпадает с портом блока


def test_route_ok_for_superuser(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Суперпользователь проходит require_roles всегда (см. deps.require_roles)."""
    r = client.get(
        f"{settings.API_V1_STR}/search",
        params={"q": "забег"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200


def test_route_missing_query_param_is_422(
    client: TestClient, crew_token_headers: dict[str, str]
) -> None:
    """QA п.11: кривое тело/параметры → 422."""
    r = client.get(f"{settings.API_V1_STR}/search", headers=crew_token_headers)
    assert r.status_code == 422


def test_route_invalid_k_is_422(
    client: TestClient, crew_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/search",
        params={"q": "яма", "k": 0},
        headers=crew_token_headers,
    )
    assert r.status_code == 422


def test_route_invalid_kind_is_422(
    client: TestClient, crew_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/search",
        params={"q": "яма", "kind": "not-a-kind"},
        headers=crew_token_headers,
    )
    assert r.status_code == 422


def test_no_network_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """QA п.8: сеть запрещена — любой httpx-вызов должен упасть, если бы блок его делал."""
    import httpx

    def deny(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("D2 L0 не должен ходить в сеть")

    monkeypatch.setattr(httpx.Client, "get", deny)
    monkeypatch.setattr(httpx.Client, "post", deny)
    assert search.search("яма у школы", k=3)
