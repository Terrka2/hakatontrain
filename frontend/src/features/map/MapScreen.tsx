import { MapPinOff } from "lucide-react"
import { useCallback } from "react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { setUiState, useUiState } from "@/lib/ui-state"
import { cn } from "@/lib/utils"
import { PRIORITY } from "@/theme/priority"
import { CityMap } from "./CityMap"
import { ClusterCard } from "./ClusterCard"
import type { BBox } from "./types"
import { useClusters } from "./useClusters"

/** Легенда: три ступени приоритета и сколько всего проблем на карте. */
function Legend({ total }: { total: number }) {
  return (
    <div className="pointer-events-auto flex max-w-[calc(100%-3.5rem)] items-center gap-3 rounded-full border bg-background/95 px-3 py-1.5 text-xs shadow-sm backdrop-blur">
      <span className="font-medium tabular-nums">{total} на карте</span>
      {(["high", "mid", "low"] as const).map((level) => (
        <span
          key={level}
          className="flex items-center gap-1 text-muted-foreground"
          title={PRIORITY[level].label}
        >
          <span
            className={cn("size-2.5 rounded-full", PRIORITY[level].bg)}
            aria-hidden
          />
          <span className="hidden sm:inline">{PRIORITY[level].label}</span>
        </span>
      ))}
    </div>
  )
}

/** Главный экран: карта на всю площадь, панель — справа на десктопе, снизу на телефоне. */
export function MapScreen() {
  const { data, isPending, error, refetch } = useClusters()
  const { selected_cluster_id: selectedId } = useUiState()
  const selected = data?.find((c) => c.id === selectedId) ?? null

  const select = useCallback(
    (id: string | null) => setUiState({ selected_cluster_id: id }),
    [],
  )
  const onBounds = useCallback((bbox: BBox) => setUiState({ bbox }), [])

  let panel: React.ReactNode = null
  if (isPending) panel = <Skeleton rows={3} />
  else if (error)
    panel = (
      <ErrorState
        title="Карта без данных"
        error={error}
        onRetry={() => refetch()}
      />
    )
  else if (!data?.length)
    panel = (
      <EmptyState
        icon={MapPinOff}
        title="Открытых проблем нет"
        hint="Новые обращения появятся здесь сами."
      />
    )
  else if (selected)
    panel = <ClusterCard cluster={selected} onClose={() => select(null)} />

  return (
    <div
      className="relative -m-6 h-[calc(100dvh-4rem)] overflow-hidden md:-m-8"
      data-testid="map-screen"
    >
      <CityMap
        className="absolute inset-0"
        layers={
          data
            ? [
                {
                  kind: "clusters",
                  items: data,
                  selectedId: selectedId ?? undefined,
                },
              ]
            : []
        }
        onSelectCluster={select}
        onBoundsChange={onBounds}
      />
      <div className="pointer-events-none absolute inset-x-3 top-3 flex justify-start">
        {data && data.length > 0 && <Legend total={data.length} />}
      </div>
      {panel && (
        <aside
          data-testid="map-panel"
          className={cn(
            "absolute inset-x-0 bottom-0 max-h-[55%] overflow-y-auto rounded-t-2xl border-t bg-background p-4 pb-[max(1rem,env(safe-area-inset-bottom))] shadow-lg",
            "md:inset-x-auto md:bottom-4 md:right-4 md:top-14 md:max-h-none md:w-96 md:rounded-2xl md:border",
          )}
        >
          <div
            className="mx-auto mb-3 h-1 w-10 rounded-full bg-muted-foreground/40 md:hidden"
            aria-hidden
          />
          {panel}
        </aside>
      )}
    </div>
  )
}
