// Данные карты. Единственное место, где фича знает про mock и про API.
import { apiGet, USE_MOCK } from "@/lib/api"
import type { ClusterOut } from "@/lib/contracts"
import { getMockState, later } from "@/lib/mock-store"

export async function fetchClusters(): Promise<ClusterOut[]> {
  if (USE_MOCK) return later(getMockState().items)
  return apiGet<ClusterOut[]>("/api/v1/clusters", { sort: "priority" })
}
