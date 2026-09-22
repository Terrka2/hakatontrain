// Слои маршрутов: CrewRoute → GeoJSON для maplibre. Пройденная часть и предстоящая — разные линии.
import type { CrewRoute, GeoPoint } from "@/lib/contracts"

type LineFeature = {
  type: "Feature"
  properties: { crew: string; part: "done" | "ahead"; color: string }
  geometry: { type: "LineString"; coordinates: [number, number][] }
}
export type RouteCollection = {
  type: "FeatureCollection"
  features: LineFeature[]
}

/** Имя CSS-токена цвета бригады по её индексу в списке бригад. */
export function routeColorVar(index: number): string {
  return `--crew-${(((index % 3) + 3) % 3) + 1}`
}

const coords = (pts: GeoPoint[]): [number, number][] =>
  pts.map((p) => [p.lon, p.lat])

/** Геометрия делится на «сделано» (до последней закрытой остановки) и «впереди». Цвет — токен, разрешается на карте. */
export function routeFeatures(
  routes: CrewRoute[],
  crewOrder: string[],
): RouteCollection {
  const features: LineFeature[] = []
  for (const r of routes) {
    if (r.geometry.length < 2) continue
    const idx = Math.max(0, crewOrder.indexOf(r.crew_id))
    const color = routeColorVar(idx)
    const lastDone = r.stops.reduce(
      (acc, s, i) => (s.status === "done" || s.status === "failed" ? i : acc),
      -1,
    )
    // geometry[0] — старт бригады, geometry[i+1] — остановка i.
    const split = lastDone + 1
    if (split > 0)
      features.push({
        type: "Feature",
        properties: { crew: r.crew_id, part: "done", color },
        geometry: {
          type: "LineString",
          coordinates: coords(r.geometry.slice(0, split + 1)),
        },
      })
    if (split < r.geometry.length - 1)
      features.push({
        type: "Feature",
        properties: { crew: r.crew_id, part: "ahead", color },
        geometry: {
          type: "LineString",
          coordinates: coords(r.geometry.slice(split)),
        },
      })
  }
  return { type: "FeatureCollection", features }
}

/** oklch-токены maplibre не понимает: переводим через canvas в rgb. Вне браузера — прозрачный. */
export function resolveCssColor(varName: string): string {
  if (typeof document === "undefined") return "transparent"
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue(varName)
    .trim()
  const ctx = document.createElement("canvas").getContext("2d")
  if (!ctx || !raw) return "transparent"
  ctx.fillStyle = raw
  return String(ctx.fillStyle)
}
