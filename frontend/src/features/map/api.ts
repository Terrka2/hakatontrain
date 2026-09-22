// Данные карты. Единственное место, где фича знает про mock и про API.

import { apiGet, USE_MOCK } from "@/lib/api"
import demo from "@/mocks/demo_city.json"
import { clustersFromDemo } from "./clusters"
import type { ClusterOut, DemoCity } from "./types"

export async function fetchClusters(): Promise<ClusterOut[]> {
  if (USE_MOCK) return clustersFromDemo(demo as DemoCity)
  return apiGet<ClusterOut[]>("/api/v1/clusters", { sort: "priority" })
}
