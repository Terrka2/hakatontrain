# Референсы F1 · Карта и каркас экрана

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/frontend_feature/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```tsx
// frontend/src/features/map/index.ts
export type MapLayer =
  | { kind: "clusters"; items: ClusterOut[]; selectedId?: string }
  | { kind: "routes"; routes: CrewRoute[] }
  | { kind: "crew"; route: CrewRoute }              // маршрут одной бригады: пройденное серым, следующее — ярко
export function CityMap(props: { layers: MapLayer[]; onSelectCluster?: (id: string) => void; onBoundsChange?: (bbox: BBox) => void }): JSX.Element
export function useUiState(): UIState          // bbox + выбранный кластер + фильтры → уходит ассистенту
```
Библиотека карты: `maplibre-gl` + `react-map-gl/maplibre`, тайлы OSM. Цвет маркера = приоритет (3 ступени), размер = число обращений.
Данные — через сгенерированный клиент `frontend/src/client` и TanStack Query. `VITE_USE_MOCK=true` → `frontend/src/mocks/demo_city.json`.

Переключатель уровня: `VITE_USE_MOCK=true|false`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `frontend/src/features/map/**`
- `frontend/src/routes/_layout/index.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/ui-state.ts`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. При `VITE_USE_MOCK=true` видны 13 маркеров; самые красные — у лицея и у детсада.
2. Экран работает на 390 px: карта на весь экран, панель — выезжающая снизу.
3. Состояния loading / empty / error отрисованы, а не белый экран.
4. `tsc --noEmit` и `npm run build` зелёные.
