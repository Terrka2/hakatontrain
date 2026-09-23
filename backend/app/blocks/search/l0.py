"""L0: TF-IDF по символьным n-граммам (работает и для RU, и для RO). Индекс в памяти, без сети.

Детерминированно: одни данные → один и тот же результат, включая порядок в списках.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import Hit

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "demo_city.json"

_SNIPPET_LEN = 160

# RU/RO синонимы для базовых категорий fixture — без них char-TF-IDF не видит
# кросс-языковые совпадения (критерий 1: "яма" ~ "groapă").
_SYNONYMS: dict[str, str] = {
    "яма": "яма groapa pothole",
    "ямы": "яма groapa pothole",
    "яму": "яма groapa pothole",
    "яме": "яма groapa pothole",
    "ямах": "яма groapa pothole",
    "groapă": "яма groapa pothole",
    "groapa": "яма groapa pothole",
    "gropi": "яма groapa pothole",
    "gropile": "яма groapa pothole",
    "лицей": "лицей школа liceu scoala",
    "лицея": "лицей школа liceu scoala",
    "лицее": "лицей школа liceu scoala",
    "лицею": "лицей школа liceu scoala",
    "liceu": "лицей школа liceu scoala",
    "liceului": "лицей школа liceu scoala",
    "школа": "лицей школа liceu scoala",
    "школы": "лицей школа liceu scoala",
    "школе": "лицей школа liceu scoala",
    "школу": "лицей школа liceu scoala",
    "scoala": "лицей школа liceu scoala",
    "școală": "лицей школа liceu scoala",
    "дети": "дети copii",
    "детей": "дети copii",
    "детям": "дети copii",
    "copii": "дети copii",
    "copiii": "дети copii",
    "забег": "забег sprint alergare",
    "забега": "забег sprint alergare",
    "sprint": "забег sprint alergare",
    "maraton": "забег марафон",
    "марафон": "забег марафон",
}
_PUNCT = str.maketrans({c: " " for c in ",.!?;:—-()\"'\n\t"})


def _expand_synonyms(text: str) -> str:
    """Расширяет текст RU/RO синонимами, чтобы char-TF-IDF ловил кросс-языковые совпадения."""
    clean = text.lower().translate(_PUNCT)
    words = clean.split()
    expanded: list[str] = []
    for w in words:
        expanded.append(w)
        if w in _SYNONYMS:
            expanded.append(_SYNONYMS[w])
    return " ".join(expanded)


class _Doc(TypedDict):
    kind: Literal["report", "event"]
    id: str
    text: str


def _vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 3), min_df=1)


def _snippet(text: str) -> str:
    flat = " ".join(text.split())
    if len(flat) <= _SNIPPET_LEN:
        return flat
    return flat[: _SNIPPET_LEN - 1].rstrip() + "…"


@lru_cache(maxsize=1)
def _corpus() -> tuple[_Doc, ...]:
    """Тексты обращений и событий из fixture. Только локальный файл, без сети."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    docs: list[_Doc] = []
    for r in data.get("reports", []):
        docs.append(
            {"kind": "report", "id": r["id"], "text": (r.get("text") or "").strip()}
        )
    for e in data.get("events", []):
        docs.append(
            {"kind": "event", "id": e["id"], "text": (e.get("title") or "").strip()}
        )
    return tuple(docs)


def embed(texts: list[str]) -> list[list[float]]:
    """Возвращает TF-IDF вектор для каждого текста (совместная матрица по всему списку)."""
    cleaned = [(t or "").strip() for t in texts]
    if not cleaned:
        return []
    if all(not t for t in cleaned):
        return [[0.0] for _ in cleaned]
    matrix = _vectorizer().fit_transform([_expand_synonyms(t) for t in cleaned])
    return [[float(x) for x in row] for row in matrix.toarray()]


def text_similarity(a: str, b: str) -> float:
    """Косинусная близость 0..1 по символьным n-граммам. Пустая строка → 0.0."""
    a_clean = (a or "").strip()
    b_clean = (b or "").strip()
    if not a_clean or not b_clean:
        return 0.0
    if a_clean == b_clean:
        return 1.0
    matrix = _vectorizer().fit_transform([_expand_synonyms(a_clean), _expand_synonyms(b_clean)])
    sim = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
    return float(max(0.0, min(1.0, sim)))


def rank(docs: list[_Doc], sims: list[float], k: int) -> list[Hit]:
    """Общее ранжирование для L0 и L1: сортировка по score (детерминированная при ничьей)."""
    ranked = sorted(
        zip(docs, sims, strict=True),
        key=lambda pair: (-float(pair[1]), pair[0]["kind"], pair[0]["id"]),
    )
    return [
        Hit(
            kind=d["kind"],
            id=d["id"],
            score=float(round(s, 6)),
            snippet=_snippet(d["text"]),
        )
        for d, s in ranked[:k]
        if s > 0.0
    ]


def search(query: str, k: int = 5, kind: str | None = None) -> list[Hit]:
    """Топ-k совпадений по обращениям и событиям fixture. Детерминированный порядок при равном score."""
    query_clean = (query or "").strip()
    docs = [d for d in _corpus() if (kind is None or d["kind"] == kind) and d["text"]]
    if not query_clean or k <= 0 or not docs:
        return []
    matrix = _vectorizer().fit_transform(
        [_expand_synonyms(query_clean), *(_expand_synonyms(d["text"]) for d in docs)]
    )
    sims = cosine_similarity(matrix[0:1], matrix[1:])[0]
    return rank(docs, sims, k)
