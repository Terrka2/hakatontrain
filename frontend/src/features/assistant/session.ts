// Состояние разговора с оператором. Чистый редьюсер — тестируется node --test без React.
import type {
  AssistantRequest,
  AssistantResponse,
  PendingAction,
  UIAction,
  UIStateDto,
} from "@/lib/contracts"

export type Message =
  | { role: "user"; text: string }
  | { role: "assistant"; text: string; trace: string[]; actions: UIAction[] }
  | { role: "error"; text: string }

export type SessionState = {
  messages: Message[]
  /** Действие, которое оператор сам сделать не вправе: ждёт решения человека. */
  pending: PendingAction | null
  busy: boolean
}

export const initialSession: SessionState = {
  messages: [],
  pending: null,
  busy: false,
}

export type SessionEvent =
  | { type: "send"; text: string }
  | { type: "reply"; response: AssistantResponse }
  | { type: "fail"; text: string }
  | { type: "decide"; approve: boolean }

export const ERROR_TEXT = "Оператор не ответил. Попробуйте ещё раз."

export function reduceSession(
  state: SessionState,
  event: SessionEvent,
): SessionState {
  switch (event.type) {
    case "send":
      return {
        ...state,
        busy: true,
        messages: [...state.messages, { role: "user", text: event.text }],
      }
    case "reply":
      return {
        busy: false,
        pending: event.response.pending,
        messages: [
          ...state.messages,
          {
            role: "assistant",
            text: event.response.text,
            trace: event.response.trace,
            actions: event.response.actions,
          },
        ],
      }
    case "fail":
      return {
        ...state,
        busy: false,
        messages: [...state.messages, { role: "error", text: event.text }],
      }
    case "decide":
      // Карточка закрывается в любом случае; запрос confirm уходит только при approve — это решает вызывающий код.
      return { ...state, pending: null, busy: event.approve }
  }
}

/** Запрос уходит с тем, что человек видит на экране: роль, bbox, выбранный кластер, фильтры. */
export function buildRequest(
  sessionId: string,
  message: string,
  ui: UIStateDto,
): AssistantRequest {
  return {
    session_id: sessionId,
    message: message.trim(),
    ui_state: {
      role: ui.role,
      bbox: ui.bbox,
      selected_cluster_id: ui.selected_cluster_id,
      filters: { ...ui.filters },
    },
  }
}
