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

/** oklch-токены maplibre не понимает: рисуем пиксель на canvas и читаем его как rgb. Вне браузера — прозрачный. */
const colorCache = new Map<string, string>()
export function resolveCssColor(varName: string): string {
  if (typeof document === "undefined") return "transparent"
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue(varName)
    .trim()
  if (!raw) return "transparent"
  const key = `${varName}:${raw}`
  const hit = colorCache.get(key)
  if (hit) return hit
  const canvas = document.createElement("canvas")
  canvas.width = 1
  canvas.height = 1
  const ctx = canvas.getContext("2d", { willReadFrequently: true })
  if (!ctx) return "transparent"
  ctx.fillStyle = raw
  ctx.fillRect(0, 0, 1, 1)
  const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data
  const rgb = `rgba(${r}, ${g}, ${b}, ${(a / 255).toFixed(2)})`
  colorCache.set(key, rgb)
  return rgb
}
