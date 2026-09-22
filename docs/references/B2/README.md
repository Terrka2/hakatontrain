# Референсы B2 · Гео-утилиты

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```python
# backend/app/blocks/geo/__init__.py
def haversine_m(a: GeoPoint, b: GeoPoint) -> float: ...
def centroid(points: list[GeoPoint]) -> GeoPoint: ...
def within(center: GeoPoint, points: list[GeoPoint], radius_m: float) -> list[int]: ...       # индексы
def distance_to_polyline_m(p: GeoPoint, line: list[GeoPoint]) -> tuple[float, float]: ...     # (до линии, от начала вдоль линии)
def geocode(address: str) -> GeoPoint | None: ...
def h3_cell(p: GeoPoint, res: int = 9) -> str: ...
```

Переключатель уровня: `GEOCODER=off|nominatim`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `backend/app/blocks/geo/**`
- `backend/tests/blocks/geo/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. `haversine_m` между `r001` и `r002` из fixture = 27–31 м; между `r007` и `r010` = 385–393 м.
2. `within` вокруг события `e1` с радиусом 400 м находит `r012` и `r013` и не находит `r001`.
3. `distance_to_polyline_m` для точки на линии = 0 ± 1 м.
4. При `GEOCODER=off` или ошибке сети `geocode` возвращает `None` без исключения.
