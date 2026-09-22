// Данные очереди. Единственное место, где фича знает про mock и про API.
import { client } from "@/client/client.gen"
import { apiGet, USE_MOCK } from "@/lib/api"
import type { ClusterOut, Report } from "@/lib/contracts"
import { getMockState, later } from "@/lib/mock-store"

export async function fetchQueue(): Promise<ClusterOut[]> {
  if (USE_MOCK) return later(getMockState().items)
  return apiGet<ClusterOut[]>("/api/v1/clusters", { sort: "priority" })
}

export async function fetchReports(): Promise<Report[]> {
  if (USE_MOCK) return later(getMockState().reports)
  return apiGet<Report[]>("/api/v1/reports")
}

export type ReviewDecision = "accept" | "reject"

/** Решение руководителя по сомнительному кластеру. На mock — только локально, сервер ничего не хранит. */
export async function reviewCluster(
  id: string,
  decision: ReviewDecision,
): Promise<void> {
  if (USE_MOCK) return later(undefined)
  await client.post({
    url: `/api/v1/clusters/${id}/review`,
    query: { decision },
    throwOnError: true,
  })
}
