# Референсы X1 · Мероприятия (дополнительный)

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`
- `docs/references/_patterns/frontend_feature/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```python
# backend/app/blocks/events/__init__.py
def get_events(start: datetime, end: datetime) -> list[Event]: ...
def enrich_context(ctx: Context) -> Context: ...                                   # добавляет ctx.events
def apply_deadlines(jobs: list[Job], clusters: list[Cluster], events: list[Event]) -> tuple[list[Job], list[Decision]]: ...
```
- фактор `EX` (файл `priority/factors/ex.py`): кластер в радиусе события, начинающегося ≤ 72 ч → `min(1, expected_people / 1000)`, иначе 0; нет событий → `None`;
- `apply_deadlines`: задача в радиусе события, начинающегося ≤ 72 ч → `deadline = event.starts_at`, `Decision.kind="deadline"`.
Роуты (`/api/v1/events`): `GET /events?from=&to=`, `POST /events` (supervisor).

Переключатель уровня: `OPTIONAL_BLOCKS=on|off`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `backend/app/blocks/events/**`
- `backend/app/api/routes/events.py`
- `backend/app/blocks/priority/factors/ex.py`
- `backend/tests/blocks/events/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. `get_events` возвращает `e1` для 26–28 сентября 2026 и пусто для октября.
2. Задачи по `r012` и `r013` получают `deadline = начало e1` (`expect_optional.event_deadline_reports`).
3. Фактор `EX` для кластера `r012` = 1.0, в `evidence` назван забег; для `r001` = 0.
4. `OPTIONAL_BLOCKS=off` → `ctx.events == []`, роуты отдают 404, ядро работает как раньше.
