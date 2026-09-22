// Данные панели. Единственное место, где фича знает про mock и про API.
import { USE_MOCK } from "@/lib/api"
import type { AssistantRequest, AssistantResponse } from "@/lib/contracts"
import { askAssistant, confirmPending, later } from "@/lib/mock-store"

const TIMEOUT_MS = 8_000

/** POST с таймаутом: тот же baseURL и токен, что у сгенерированного клиента. */
async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS)
  try {
    const token = localStorage.getItem("access_token")
    const res = await fetch(`${import.meta.env.VITE_API_URL ?? ""}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    })
    if (!res.ok) throw new Error(`assistant: ${res.status}`)
    return (await res.json()) as T
  } finally {
    clearTimeout(timer)
  }
}

export async function sendMessage(
  req: AssistantRequest,
): Promise<AssistantResponse> {
  if (USE_MOCK) return later(askAssistant(req), 400)
  return apiPost<AssistantResponse>("/api/v1/assistant", req)
}

export async function sendConfirm(
  pendingId: string,
  approve: boolean,
): Promise<AssistantResponse> {
  if (USE_MOCK) {
    const declined: AssistantResponse = {
      text: "Отменено. План остаётся черновиком.",
      actions: [],
      pending: null,
      trace: [],
    }
    return later(approve ? confirmPending(pendingId) : declined, 300)
  }
  return apiPost<AssistantResponse>("/api/v1/assistant/confirm", {
    pending_id: pendingId,
    approve,
  })
}
