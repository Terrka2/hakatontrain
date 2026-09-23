"""Уровень L0 · TF-IDF по символьным n-граммам.

Индекс строится в памяти на основе backend/app/fixtures/demo_city.json.
Работает для RU и RO без загрузки внешних нейросетевых моделей.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import Hit

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "demo_city.json"

SYNONYMS: dict[str, str] = {
    # Ямы и дорожные дефекты (RU / RO)
    "яма": "яма groapa pothole",
    "ямы": "яма groapa pothole",
    "яму": "яма groapa pothole",
    "яме": "яма groapa pothole",
    "ямах": "яма groapa pothole",
    "groapă": "яма groapa pothole",
    "groapa": "яма groapa pothole",
    "gropi": "яма groapa pothole",
    "gropile": "яма groapa pothole",
    # Школа и лицей (RU / RO)
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
    # Дети (RU / RO)
    "дети": "дети copii",
    "детей": "дети copii",
    "детям": "дети copii",
    "copii": "дети copii",
    "copiii": "дети copii",
    # Мероприятия / забег
    "забег": "забег sprint alergare",
    "забега": "забег sprint alergare",
    "sprint": "забег sprint alergare",
    "maraton": "забег марафон",
    "марафон": "забег марафон",
}


def _preprocess(text: str | None) -> str:
    """Нормализует текст и расширяет базовые двуязычные синонимы."""
    if not text or not isinstance(text, str):
        return ""
    clean = text.lower()
    for ch in [",", ".", "!", "?", ";", ":", "—", "-", "(", ")", '"', "'", "\n", "\t"]:
        clean = clean.replace(ch, " ")
    words = clean.split()
    expanded: list[str] = []
    for w in words:
        expanded.append(w)
        if w in SYNONYMS:
            expanded.append(SYNONYMS[w])
    return " ".join(expanded)


class _DocEntry:
    __slots__ = ("id", "kind", "snippet", "text")

    def __init__(
        self,
        kind: Literal["report", "event"],
        doc_id: str,
        text: str,
        snippet: str,
    ) -> None:
        self.kind = kind
        self.id = doc_id
        self.text = text
        self.snippet = snippet


class SearchIndexL0:
    """Индекс L0 в памяти на базе TF-IDF векторизатора."""

    def __init__(self, fixture_path: Path = FIXTURE_PATH) -> None:
        self.docs: list[_DocEntry] = []
        self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
        self._load_and_build_index(fixture_path)

    def _load_and_build_index(self, path: Path) -> None:
        if not path.exists():
            return

        data = json.loads(path.read_text(encoding="utf-8"))

        for r in data.get("reports", []):
            text = r.get("text", "")
            self.docs.append(
                _DocEntry(
                    kind="report",
                    doc_id=r["id"],
                    text=text,
                    snippet=text[:120],
                )
            )

        for e in data.get("events", []):
            title = e.get("title", "")
            self.docs.append(
                _DocEntry(
                    kind="event",
                    doc_id=e["id"],
                    text=title,
                    snippet=title,
                )
            )

        corpus = [_preprocess(d.text) for d in self.docs]
        if corpus:
            self.doc_vectors = self.vectorizer.fit_transform(corpus)
        else:
            self.doc_vectors = None

    def text_similarity(self, a: str | None, b: str | None) -> float:
        """Вычисляет косинусное сходство двух текстов в диапазоне [0.0, 1.0]."""
        if not a or not b or not isinstance(a, str) or not isinstance(b, str):
            return 0.0
        if not a.strip() or not b.strip():
            return 0.0
        if a.strip() == b.strip():
            return 1.0

        prep_a = _preprocess(a)
        prep_b = _preprocess(b)
        if not prep_a or not prep_b:
            return 0.0

        vec_a = self.vectorizer.transform([prep_a])
        vec_b = self.vectorizer.transform([prep_b])
        sim = float(cosine_similarity(vec_a, vec_b)[0][0])
        return max(0.0, min(1.0, round(sim, 6)))

    def search(
        self,
        query: str,
        k: int = 5,
        kind: Literal["report", "event"] | str | None = None,
    ) -> list[Hit]:
        """Семантический поиск по обращениям и событиям."""
        if k <= 0 or not query or not isinstance(query, str) or not query.strip():
            return []
        if self.doc_vectors is None or not self.docs:
            return []

        prep_q = _preprocess(query)
        if not prep_q:
            return []

        q_vec = self.vectorizer.transform([prep_q])
        scores = cosine_similarity(q_vec, self.doc_vectors)[0]

        candidates: list[tuple[float, str, _DocEntry]] = []
        for i, doc in enumerate(self.docs):
            if kind is not None and doc.kind != kind:
                continue
            candidates.append((float(scores[i]), doc.id, doc))

        # Сортировка по убыванию score, вторично по id для детерминированности
        candidates.sort(key=lambda c: (-c[0], c[1]))

        return [
            Hit(
                kind=doc.kind,
                id=doc.id,
                score=max(0.0, min(1.0, round(score, 4))),
                snippet=doc.snippet,
            )
            for score, _, doc in candidates[:k]
        ]

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Векторизует список текстов."""
        if not texts:
            return []
        prep_texts = [_preprocess(t) for t in texts]
        vecs = self.vectorizer.transform(prep_texts)
        return vecs.toarray().tolist()


# Инициализация синглтона индекса L0 в памяти при загрузке модуля
_index = SearchIndexL0()


def embed(texts: list[str]) -> list[list[float]]:
    return _index.embed(texts)


def text_similarity(a: str, b: str) -> float:
    return _index.text_similarity(a, b)


def search(
    query: str,
    k: int = 5,
    kind: Literal["report", "event"] | str | None = None,
) -> list[Hit]:
    return _index.search(query, k=k, kind=kind)
