// Блок F1 · Карта и каркас экрана. Публичный интерфейс фичи — только то, что экспортировано здесь.
// Контракт: docs/contracts/F1_map.md

export { useUiState } from "@/lib/ui-state"
export { CityMap } from "./CityMap"
export { MapScreen } from "./MapScreen"
export type { BBox, ClusterOut, CrewRoute, MapLayer } from "./types"
export { useClusters } from "./useClusters"
