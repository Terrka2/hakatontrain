// Данные пульта. Единственное место, где фича знает про mock и про API.
import { client } from "@/client/client.gen"
import { apiGet, USE_MOCK } from "@/lib/api"
import type { Crew, OperatorRun, Plan } from "@/lib/contracts"
import type { WeatherMode } from "@/lib/mock-city"
import {
  approvePlan,
  demo,
  getMockState,
  later,
  resetDemo,
  selectApproved,
  selectDraft,
  setWeather,
} from "@/lib/mock-store"

async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  const res = (await client.post({
    url,
    body,
    throwOnError: true,
  })) as unknown as { data: T }
  return res.data
}

export async function fetchRuns(): Promise<OperatorRun[]> {
  if (USE_MOCK) return later(getMockState().runs)
  return apiGet<OperatorRun[]>("/api/v1/operator/runs")
}

export async function fetchDraft(): Promise<Plan | null> {
  if (USE_MOCK) return later(selectDraft(getMockState()))
  return apiGet<Plan | null>("/api/v1/plan", { status: "draft" })
}

export async function fetchApproved(): Promise<Plan | null> {
  if (USE_MOCK) return later(selectApproved(getMockState()))
  return apiGet<Plan | null>("/api/v1/plan", { status: "approved" })
}

export async function fetchCrews(): Promise<Crew[]> {
  if (USE_MOCK) return later(demo.crews)
  return apiGet<Crew[]>("/api/v1/crew")
}

export async function approve(planId: string): Promise<void> {
  if (USE_MOCK) {
    approvePlan(planId)
    return
  }
  await apiPost(`/api/v1/plan/${planId}/approve`)
}

export async function switchWeather(mode: WeatherMode): Promise<void> {
  if (USE_MOCK) {
    setWeather(mode)
    return
  }
  await apiPost("/api/v1/context/weather", { mode })
}

export async function resetAll(): Promise<void> {
  if (USE_MOCK) {
    resetDemo()
    return
  }
  await apiPost("/api/v1/utils/reset")
}
