# Референсы B1 · Парсер и импорт обращений

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```python
# backend/app/blocks/ingest/__init__.py
class IngestResult(BaseModel):
    reports: list[Report]
    rejected: list[dict]        # {"row": int, "reason": str}

def load_fixture() -> list[Report]: ...
def parse_file(path: Path, mapping: dict[str, str] | None = None) -> IngestResult: ...
def normalize(raw: dict, mapping: dict[str, str]) -> Report: ...   # бросает ValueError с понятной причиной
```
Роуты (`/api/v1/reports`):
- `POST /reports/import` (файл) → `{imported, rejected}` (supervisor); после импорта — `operator_run("import")`
- `GET /reports?status=&category=&bbox=` → `list[Report]`
- `POST /reports` → создать обращение, сразу `verification.status="unverified"`; после — `operator_run("new_report")`
- `POST /reports/{id}/confirm` → `confirmations += 1` («у меня тоже / всё ещё там»)

Переключатель уровня: `USE_MOCK=true|false`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `backend/app/blocks/ingest/**`
- `backend/app/api/routes/reports.py`
- `backend/tests/blocks/ingest/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. `load_fixture()` возвращает 16 `Report`, из них `expect.open_reports` открытых.
2. CSV с колонками на румынском/русском парсится через `mapping.yaml` без правки кода.
3. Строка без координат и строка с неизвестной категорией попадают в `rejected` с причиной, импорт не падает.
4. Повторный импорт того же файла не создаёт дублей (по `id`).
