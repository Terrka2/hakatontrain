import "maplibre-gl/dist/maplibre-gl.css"

import type { StyleSpecification } from "maplibre-gl"
import { useCallback, useEffect, useMemo, useRef } from "react"
import MapGL, { type MapRef, NavigationControl } from "react-map-gl/maplibre"

import { ClusterMarker } from "./ClusterMarker"
import type { BBox, ClusterOut, MapLayer } from "./types"

/** Кишинёв, центр. */
export const CHISINAU = { longitude: 28.84, latitude: 47.024, zoom: 12.6 }

const OSM_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
}

/** Рамка вокруг всех кластеров, чтобы при загрузке были видны все маркеры. */
function boundsOf(items: ClusterOut[]): BBox | null {
  if (!items.length) return null
  const lons = items.map((c) => c.centroid.lon)
  const lats = items.map((c) => c.centroid.lat)
  return [
    Math.min(...lons),
    Math.min(...lats),
    Math.max(...lons),
    Math.max(...lats),
  ]
}

type Props = {
  layers: MapLayer[]
  onSelectCluster?: (id: string) => void
  onBoundsChange?: (bbox: BBox) => void
  className?: string
}

/** Один компонент карты на всё приложение; остальные фичи только передают ему слои. */
export function CityMap({
  layers,
  onSelectCluster,
  onBoundsChange,
  className,
}: Props) {
  const mapRef = useRef<MapRef>(null)
  const clusterLayer = layers.find((l) => l.kind === "clusters")
  // Срочные маркеры поверх плановых: порядок в DOM = порядок наложения.
  const ordered = useMemo(
    () =>
      (clusterLayer?.items ?? [])
        .slice()
        .sort((a, b) => a.score - b.score || a.id.localeCompare(b.id)),
    [clusterLayer?.items],
  )
  const fitAll = useCallback(() => {
    const box = boundsOf(ordered)
    const map = mapRef.current
    if (box && map?.loaded())
      map.fitBounds(box, { padding: 56, maxZoom: 15, duration: 0 })
  }, [ordered])
  // Подгонка один раз на новый набор кластеров (ordered мемоизирован по items); до загрузки карты — из onLoad.
  useEffect(fitAll, [fitAll])
  const reportBounds = useCallback(() => {
    const b = mapRef.current?.getBounds()
    if (b && onBoundsChange)
      onBoundsChange([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()])
  }, [onBoundsChange])
  const onLoad = useCallback(() => {
    fitAll()
    reportBounds()
  }, [fitAll, reportBounds])

  return (
    <div className={className} data-testid="city-map">
      <MapGL
        ref={mapRef}
        initialViewState={CHISINAU}
        mapStyle={OSM_STYLE}
        onMoveEnd={reportBounds}
        onLoad={onLoad}
        attributionControl={{ compact: true }}
        style={{ width: "100%", height: "100%" }}
      >
        <NavigationControl position="top-right" showCompass={false} />
        {ordered.map((c) => (
          <ClusterMarker
            key={c.id}
            cluster={c}
            selected={c.id === clusterLayer?.selectedId}
            onSelect={onSelectCluster}
          />
        ))}
      </MapGL>
    </div>
  )
}
