// Типы данных карты. Сервер их отдаёт по контракту (Cluster + Priority, CrewRoute);
// пока B0 не отдаёт openapi для /clusters, форма зафиксирована здесь, поля — как в contracts/models.py.
import type { BBox } from "@/lib/ui-state"

export type { BBox }

export type GeoPoint = { lat: number; lon: number }

export type ClusterOut = {
  id: string
  category: string
  centroid: GeoPoint
  report_ids: string[]
  status: "open" | "planned" | "in_progress" | "resolved"
  score: number
  needs_review: boolean
  address: string | null
  summary: string
}

export type RouteStop = {
  job_id: string
  location: GeoPoint
  status: "pending" | "arrived" | "done" | "failed"
}

export type CrewRoute = {
  crew_id: string
  stops: RouteStop[]
  geometry: GeoPoint[]
}

export type MapLayer =
  | { kind: "clusters"; items: ClusterOut[]; selectedId?: string }
  | { kind: "routes"; routes: CrewRoute[] }
  | { kind: "crew"; route: CrewRoute }

/** Кусок fixture demo_city.json, который нужен карте на L0. */
export type DemoReport = {
  id: string
  category: string
  text: string
  location: GeoPoint
  address: string | null
  status: string
  confirmations: number
}

export type DemoCity = {
  reports: DemoReport[]
  infrastructure: { id: string; kind: string; location: GeoPoint }[]
  expect: { dup_trio: string[]; suspicious_report: string }
}
