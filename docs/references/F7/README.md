# Референсы F7 · Экран жителя (дополнительный)

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`
- `docs/references/_patterns/frontend_feature/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```tsx
export function TripPlanner(): JSX.Element        // A и B кликом по карте или адресом → Trip
export function HazardList(props: { hazards: HazardOnRoute[]; onConfirm: (clusterId: string) => void }): JSX.Element
export function EventsList(props: { items: Event[] }): JSX.Element
export function ReportForm(): JSX.Element         // категория, текст, точка на карте, фото
```

Переключатель уровня: `VITE_USE_MOCK`, `OPTIONAL_BLOCKS`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `frontend/src/features/citizen/**`
- `frontend/src/routes/_layout/trip.tsx`
- `frontend/src/routes/_layout/events.tsx`
- `frontend/src/routes/_layout/report.tsx`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. Маршрут через центр показывает яму `r012` и событие `e1` (на дату 27.09).
2. «Всё ещё там» увеличивает счётчик; после прохода оператора приоритет кластера вырос.
3. Роль citizen не видит экранов руководителя и бригады.
4. Удобно на 390 px.
