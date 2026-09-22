# Референсы B8 · Работа бригад: маршрут, статусы, «не могу»

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```python
# backend/app/blocks/fieldwork/__init__.py
def get_crew_route(crew_id: str) -> CrewRoute | None: ...          # только из плана со status="approved"
def apply_update(update: JobUpdate) -> RouteStop: ...               # меняет статус остановки, валидирует переход
def progress(plan_id: str) -> dict[str, dict[str, int]]: ...        # crew_id -> {"done": 2, "failed": 1, "pending": 3}
```
Допустимые переходы: `pending → arrived → done | failed`; `pending → failed`. Остальное → ошибка 409.
`done` без `photo_url` → 422. `failed` без `reason` → 422. `needs_other_skill` без `needs_skill` → 422.
`done` → кластеры задачи получают `status="resolved"`, их обращения — `resolved`.
`failed` → вызвать `app.blocks.operator.operator_run("job_update", now, update)` (перестройку делает оператор, не этот блок).

Роуты (`/api/v1/crew`): `GET /crew/me/route` (роль crew — свой маршрут по `crew_id` пользователя); `POST /crew/jobs/{job_id}/status` (тело `JobUpdate`); `GET /crew/progress` (supervisor).

Переключатель уровня: `USE_MOCK=true|false`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `backend/app/blocks/fieldwork/**`
- `backend/app/api/routes/crew.py`
- `backend/tests/blocks/fieldwork/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. Бригада c1 видит только свои остановки и только из утверждённого плана; при одном лишь черновике — пустой маршрут с понятным сообщением.
2. `done` с фото → остановка `done`, кластеры задачи `resolved`.
3. `done` без фото, `failed` без причины, переход `done → arrived` → ошибки 422 / 409, данные не изменились.
4. `failed` → зафиксирован вызов `operator_run("job_update", …)` (в тесте — мок) ровно один раз.
5. Бригада c1 не может отметить задачу бригады c2 → 403.
