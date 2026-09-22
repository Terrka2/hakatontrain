// Что сейчас на экране (UIState из контрактов). Так ассистент «видит карту» — без пикселей.
// Один стор на приложение: карта пишет bbox и выбор, остальные фичи читают.
import { useSyncExternalStore } from "react"

/** min_lon, min_lat, max_lon, max_lat */
export type BBox = [number, number, number, number]

export type UIState = {
  role: "supervisor" | "crew" | "citizen"
  bbox: BBox | null
  selected_cluster_id: string | null
  filters: Record<string, unknown>
}

let state: UIState = {
  role: "supervisor",
  bbox: null,
  selected_cluster_id: null,
  filters: {},
}
const listeners = new Set<() => void>()

function emit() {
  for (const l of listeners) l()
}

export function setUiState(patch: Partial<UIState>): void {
  state = { ...state, ...patch }
  emit()
}

export function getUiState(): UIState {
  return state
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useUiState(): UIState {
  return useSyncExternalStore(subscribe, getUiState, getUiState)
}
