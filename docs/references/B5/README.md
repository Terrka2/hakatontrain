# Референсы B5 · Контекст: погода и соц. объекты

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```python
# backend/app/blocks/context/__init__.py
def get_weather(point: GeoPoint, at: datetime) -> Weather | None: ...
def build_context(now: datetime) -> Context: ...            # events=[] — их добавляет только блок X1
def apply_weather_rules(jobs: list[Job], weather: Weather | None) -> tuple[list[Job], list[Decision]]: ...
```
Правила погоды — таблица в `backend/app/blocks/context/weather_rules.yaml`, не в коде:
- осадки ≥ 5 мм → задачи навыка `road` категории `pothole` откладываются (`Decision.kind="defer"`), убираются из списка;
- ветер ≥ 15 м/с → задачи `tree`: `priority = min(100, priority + 20)` (`kind="boost"`);
- осадки ≥ 5 мм → `service_min × 1.3` для остальных уличных работ.

Роуты (`/api/v1/context`): `GET /context` → `Context`; `PUT /context/weather-scenario {scenario}` (supervisor) — для демо; смена сценария запускает проход оператора.
Источники — `backend/app/blocks/context/sources.yaml` (allowlist доменов). Ничего вне списка не запрашивается.

Переключатель уровня: `WEATHER=fixture:clear|fixture:storm|open-meteo`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `backend/app/blocks/context/**`
- `backend/app/api/routes/context.py`
- `backend/tests/blocks/context/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. `fixture:storm` → `apply_weather_rules` откладывает все `pothole`-задачи и поднимает приоритет `tree`; для каждого изменения есть `Decision` с причиной на русском.
2. `fixture:clear` → список задач не меняется, `decisions == []`.
3. `weather=None` → задачи не меняются, исключений нет.
4. Open-Meteo недоступен (мок таймаута) → возвращается fixture-погода, `source="fixture"`.
5. `build_context` возвращает 3 объекта инфраструктуры и `events == []`.
