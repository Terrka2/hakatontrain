import { ListOrdered, X } from "lucide-react"
import { useCallback } from "react"

import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { CityMap } from "@/features/map"
import useAuth from "@/hooks/useAuth"
import { setUiState, useUiState } from "@/lib/ui-state"
import { ClusterCard } from "./ClusterCard"
import { PriorityQueue } from "./PriorityQueue"
import { useQueue, useReports } from "./useQueue"

/** Очередь: карта + список «что чинить первым»; выбор открывает карточку с объяснением балла. */
export function QueueScreen() {
  const { data, isPending, error, refetch } = useQueue()
  const reports = useReports()
  const { user } = useAuth()
  const { selected_cluster_id: selectedId } = useUiState()
  const selected = data?.find((c) => c.id === selectedId) ?? null
  const select = useCallback(
    (id: string | null) => setUiState({ selected_cluster_id: id }),
    [],
  )
  const canReview =
    !user || user.role === "supervisor" || Boolean(user.is_superuser)

  let list: React.ReactNode
  if (isPending) list = <Skeleton rows={8} className="p-3" />
  else if (error)
    list = (
      <ErrorState
        title="Очередь без данных"
        error={error}
        onRetry={() => refetch()}
      />
    )
  else if (!data?.length)
    list = (
      <EmptyState
        icon={ListOrdered}
        title="Открытых проблем нет"
        hint="Новые обращения появятся здесь сами."
      />
    )
  else
    list = (
      <PriorityQueue
        items={data}
        selectedId={selectedId ?? undefined}
        onSelect={select}
      />
    )

  const card = selected && (
    <ClusterCard
      cluster={selected}
      reports={reports.data ?? []}
      canReview={canReview}
    />
  )

  return (
    <div
      className="relative -m-6 flex h-[calc(100dvh-4rem)] overflow-hidden md:-m-8"
      data-testid="queue-screen"
    >
      <div className="relative min-w-0 flex-1">
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
        />
        {/* На телефоне очередь — нижняя панель поверх карты; карточка выбранного — вместо неё. */}
        <aside
          data-testid="queue-panel"
          className="absolute inset-x-0 bottom-0 flex max-h-[60%] flex-col rounded-t-2xl border-t bg-background shadow-lg md:hidden"
        >
          <div
            className="mx-auto mt-3 h-1 w-10 shrink-0 rounded-full bg-muted-foreground/40"
            aria-hidden
          />
          {selected ? (
            <div
              key={selected.id}
              className="overflow-y-auto p-4 pb-[max(1rem,env(safe-area-inset-bottom))]"
            >
              <Button
                variant="ghost"
                size="sm"
                className="-ml-2 mb-2 min-h-12 gap-1"
                onClick={() => select(null)}
              >
                <X className="size-4" /> К очереди
              </Button>
              {card}
            </div>
          ) : (
            <div className="overflow-y-auto">{list}</div>
          )}
        </aside>
        {/* На десктопе карточка — плавающая панель над картой, очередь справа остаётся видна. */}
        {selected && (
          <aside
            key={selected.id}
            data-testid="queue-card-desktop"
            className="absolute inset-y-4 right-4 hidden w-96 overflow-y-auto rounded-2xl border bg-background p-4 shadow-lg md:block"
          >
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-2 top-2 size-10"
              aria-label="Закрыть"
              onClick={() => select(null)}
            >
              <X className="size-5" />
            </Button>
            {card}
          </aside>
        )}
      </div>
      {/* На десктопе очередь всегда справа; выбранная строка подсвечена. */}
      <aside
        className="hidden w-[26rem] shrink-0 flex-col overflow-y-auto border-l bg-background md:flex"
        data-testid="queue-desktop"
      >
        <div className="border-b px-4 py-3">
          <h1 className="text-base font-semibold">Что чинить первым</h1>
          {data && (
            <p className="text-xs text-muted-foreground">
              {data.length} проблем, сверху самые срочные
            </p>
          )}
        </div>
        {list}
      </aside>
    </div>
  )
}
