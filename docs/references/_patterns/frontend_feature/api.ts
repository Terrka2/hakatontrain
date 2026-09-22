// Данные фичи. Единственное место, где фича знает про mock и про API.
import demo from "@/mocks/demo_city.json"

export type ClusterRow = {
  id: string
  category: string
  score: number
  needs_review: boolean
}

// L0: mock включён по умолчанию. VITE_USE_MOCK=false → реальный API.
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false"

export async function fetchClusters(): Promise<ClusterRow[]> {
  if (USE_MOCK) {
    return demo.reports.map((r) => ({
      id: r.id,
      category: r.category,
      score: 50,
      needs_review: r.id === demo.expect.suspicious_report,
    }))
  }
  const res = await fetch("/api/v1/clusters?sort=priority")
  if (!res.ok) throw new Error(`clusters: ${res.status}`)
  return (await res.json()) as ClusterRow[]
}
