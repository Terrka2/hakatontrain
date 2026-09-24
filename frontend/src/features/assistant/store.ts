// Разговор живёт на уровне модуля: панель монтируется на каждом экране, а история и открытость
// переживают переходы между экранами (ассистент сам ведёт человека с карты на план и обратно).
import { useSyncExternalStore } from "react"

import {
  initialSession,
  reduceSession,
  type SessionEvent,
  type SessionState,
} from "./session"

export type DrawerState = { open: boolean; session: SessionState }

let state: DrawerState = { open: false, session: initialSession }
const listeners = new Set<() => void>()

function emit() {
  for (const l of listeners) l()
}

export function setOpen(open: boolean): void {
  state = { ...state, open }
  emit()
}

export function dispatch(event: SessionEvent): void {
  state = { ...state, session: reduceSession(state.session, event) }
  emit()
}

export function getDrawerState(): DrawerState {
  return state
}

function subscribe(l: () => void) {
  listeners.add(l)
  return () => listeners.delete(l)
}

export function useDrawerState(): DrawerState {
  return useSyncExternalStore(subscribe, getDrawerState, getDrawerState)
}
