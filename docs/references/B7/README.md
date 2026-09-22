# Референсы B7 · Навигатор жителя (дополнительный)

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`
- `docs/references/_patterns/frontend_feature/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```python
# backend/app/blocks/navigator/__init__.py
HAZARD_BUFFER_M = 40

def plan_trip(req: TripRequest, clusters: list[Cluster], priorities: dict[str, Priority], events: list[Event]) -> Trip: ...
```
`hazards` — открытые кластеры ближе `HAZARD_BUFFER_M` к линии маршрута, отсортированы по `distance_from_start_m`.
`events` — события, чей радиус пересекает маршрут и которые идут в момент `depart_at` ± 3 ч.
Роут: `POST /api/v1/trips` → `Trip`.

Переключатель уровня: `NAV=straight|ors`, `ORS_API_KEY`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `backend/app/blocks/navigator/**`
- `backend/app/api/routes/trips.py`
- `backend/tests/blocks/navigator/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. Маршрут по прямой через точку `r012` содержит его кластер в `hazards`.
2. Маршрут в 500 м от всех обращений → `hazards == []`.
3. Маршрут через центр 27.09 в 11:00 содержит `e1` в `events`; тот же маршрут 26.09 — нет.
4. `NAV=ors` без ключа → `engine="straight"`, без исключения.
