"""L1: sentence-transformers paraphrase-multilingual-MiniLM-L12-v2. Модель грузится один раз.

Ошибки НЕ ловим здесь: их ловит порт в __init__.py и откатывается на L0 (модель может быть
не скачана/недоступна — это ожидаемо на L0-каркасе).
"""

from functools import lru_cache

from . import Hit, l0

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def _model():  # type: ignore[no-untyped-def]
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_MODEL_NAME)


def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = _model().encode(list(texts), convert_to_numpy=True)
    return [[float(x) for x in row] for row in vectors]


def text_similarity(a: str, b: str) -> float:
    from sklearn.metrics.pairwise import cosine_similarity

    vectors = embed([a, b])
    sim = cosine_similarity([vectors[0]], [vectors[1]])[0][0]
    return float(max(0.0, min(1.0, sim)))


def search(query: str, k: int = 5, kind: str | None = None) -> list[Hit]:
    from sklearn.metrics.pairwise import cosine_similarity

    docs = [
        d for d in l0._corpus() if (kind is None or d["kind"] == kind) and d["text"]
    ]
    if not query.strip() or not docs or k <= 0:
        return []
    vectors = embed([query, *(d["text"] for d in docs)])
    sims = cosine_similarity([vectors[0]], vectors[1:])[0]
    return l0.rank(docs, sims, k)
