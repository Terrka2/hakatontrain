"""Блок D2 · уровень L0: TF-IDF по символьным n-граммам. Заглушка (реализация в следующей задаче)."""


def embed(texts: list[str]) -> list[list[float]]:
    raise NotImplementedError("D2 L0: embed not implemented yet")


def text_similarity(a: str, b: str) -> float:
    raise NotImplementedError("D2 L0: text_similarity not implemented yet")


def search(query: str, k: int = 5, kind: str | None = None) -> list:  # type: ignore[type-arg]
    raise NotImplementedError("D2 L0: search not implemented yet")
