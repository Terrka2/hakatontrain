import { Marker } from "react-map-gl/maplibre"

import { cn } from "@/lib/utils"
import { categoryInfo } from "@/theme/categories"
import { PRIORITY, priorityLevel } from "@/theme/priority"
import { markerSize } from "./clusters"
import type { ClusterOut } from "./types"

type Props = {
  cluster: ClusterOut
  selected: boolean
  onSelect?: (id: string) => void
}

/** Маркер кластера: цвет = ступень приоритета, размер = число обращений. */
export function ClusterMarker({ cluster, selected, onSelect }: Props) {
  const token = PRIORITY[priorityLevel(cluster.score)]
  const size = markerSize(cluster.report_ids.length)
  const label = `${categoryInfo(cluster.category).label}, приоритет ${Math.round(cluster.score)}`
  return (
    <Marker
      longitude={cluster.centroid.lon}
      latitude={cluster.centroid.lat}
      anchor="center"
      onClick={(e) => {
        e.originalEvent.stopPropagation()
        onSelect?.(cluster.id)
      }}
    >
      <button
        type="button"
        aria-label={label}
        aria-pressed={selected}
        data-cluster-id={cluster.id}
        style={{ width: size, height: size }}
        className={cn(
          "relative flex items-center justify-center rounded-full text-xs font-semibold tabular-nums shadow-marker transition-transform",
          // Зона нажатия не меньше 48 px даже у маркера в 28 px.
          "before:absolute before:-inset-2.5 before:content-['']",
          "cursor-pointer hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          token.bg,
          token.fg,
          selected && "scale-125 ring-4 ring-foreground/40",
          cluster.needs_review && "border-2 border-dashed border-background",
        )}
      >
        {cluster.report_ids.length > 1 ? cluster.report_ids.length : null}
      </button>
    </Marker>
  )
}
