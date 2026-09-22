# Референсы D2 · Эмбеддинги и семантический поиск (RAG)

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`
- `docs/references/_patterns/llm_call/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```python
# backend/app/blocks/search/__init__.py
class Hit(BaseModel):
    kind: Literal["report", "event"]
    id: str
    score: float
    snippet: str

def embed(texts: list[str]) -> list[list[float]]: ...
def text_similarity(a: str, b: str) -> float: ...            # 0..1, передаётся в B3
def search(query: str, k: int = 5, kind: str | None = None) -> list[Hit]: ...
```
Роут: `GET /api/v1/search?q=&k=` → `list[Hit]`.

Переключатель уровня: `EMBEDDER=tfidf|st`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `backend/app/blocks/search/**`
- `backend/app/api/routes/search.py`
- `backend/tests/blocks/search/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. L1: `text_similarity(r001.text, r002.text)` (RU↔RO, одна яма) > `text_similarity(r001.text, r005.text)`.
2. `search("яма у школы")` возвращает `r001` или `r003` в топ-3.
3. `search("забег")` возвращает событие `e1`.
4. Модель недоступна / не скачана → откат на tfidf без исключения.
