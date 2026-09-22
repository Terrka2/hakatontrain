// L0: кластеры и баллы из fixture, без сервера. Чистые функции — тестируются node --test.
import type { ClusterOut, DemoCity, DemoReport, GeoPoint } from "./types"

/** Базовый балл категории; итог = база + 3·подтверждения + 20, если рядом школа/сад/больница. */
const BASE_SCORE: Record<string, number> = {
  manhole: 80,
  water_leak: 60,
  tree: 55,
  pothole: 45,
  streetlight: 40,
  garbage: 35,
  public_space: 20,
}
const NEAR_INFRA_M = 150
const NEAR_INFRA_BONUS = 20

export function distanceM(a: GeoPoint, b: GeoPoint): number {
  const dLat = (b.lat - a.lat) * 111_320
  const dLon =
    (b.lon - a.lon) *
    111_320 *
    Math.cos(((a.lat + b.lat) / 2) * (Math.PI / 180))
  return Math.hypot(dLat, dLon)
}

function centroid(points: GeoPoint[]): GeoPoint {
  const n = points.length
  return {
    lat: points.reduce((s, p) => s + p.lat, 0) / n,
    lon: points.reduce((s, p) => s + p.lon, 0) / n,
  }
}

function score(
  reports: DemoReport[],
  center: GeoPoint,
  demo: DemoCity,
): number {
  const base = BASE_SCORE[reports[0].category.trim().toLowerCase()] ?? 30
  const confirmations = reports.reduce((s, r) => s + (r.confirmations ?? 0), 0)
  const nearInfra = demo.infrastructure.some(
    (i) => distanceM(i.location, center) <= NEAR_INFRA_M,
  )
  return Math.min(
    100,
    base + 3 * confirmations + (nearInfra ? NEAR_INFRA_BONUS : 0),
  )
}

/** Открытые обращения → кластеры. На L0 склеивается только expect.dup_trio (настоящую склейку делает B3). */
export function clustersFromDemo(demo: DemoCity): ClusterOut[] {
  const seen = new Set<string>()
  const open = demo.reports.filter(
    (r) => r.status === "open" && !seen.has(r.id) && seen.add(r.id),
  )
  const trio = new Set(demo.expect.dup_trio)
  const groups: DemoReport[][] = []
  const trioGroup = open.filter((r) => trio.has(r.id))
  if (trioGroup.length) groups.push(trioGroup)
  for (const r of open) if (!trio.has(r.id)) groups.push([r])

  return groups
    .map((reports): ClusterOut => {
      const center = centroid(reports.map((r) => r.location))
      const needsReview = reports.some(
        (r) => r.id === demo.expect.suspicious_report,
      )
      return {
        id: `cl-${reports[0].id}`,
        category: reports[0].category,
        centroid: center,
        report_ids: reports.map((r) => r.id),
        status: "open",
        score: score(reports, center, demo),
        needs_review: needsReview,
        address: reports.find((r) => r.address)?.address ?? null,
        summary: reports[0].text,
      }
    })
    .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id))
}

/** Диаметр маркера: 28 px за одно обращение, +6 px за каждое следующее, не больше 52 px. */
export function markerSize(reportCount: number): number {
  return Math.min(52, 28 + 6 * Math.max(0, reportCount - 1))
}
