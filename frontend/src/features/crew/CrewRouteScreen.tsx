import { ClipboardList, RefreshCw } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { CategoryIcon } from "@/components/ui/CategoryIcon"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { CityMap } from "@/features/map"
import useAuth from "@/hooks/useAuth"
import { USE_MOCK } from "@/lib/api"
import type { Job, RouteStop } from "@/lib/contracts"
import { approvePlan, getMockState, selectDraft } from "@/lib/mock-store"
import { cn } from "@/lib/utils"
import { categoryInfo } from "@/theme/categories"
import { STATUS } from "@/theme/priority"
import type { MyRoute } from "./api"
import { formatTime, nextStop, routeChanged } from "./logic"
import { NextStopCard } from "./NextStopCard"
import { StopActions } from "./StopActions"
import { useJobUpdate, useMyRoute } from "./useMyRoute"

const STOP_LABEL: Record<RouteStop["status"], { text: string; bg: string }> = {
  pending: { text: "Впереди", bg: STATUS.open.bg },
  arrived: { text: "На месте", bg: STATUS.in_progress.bg },
  done: { text: "Сделано", bg: STATUS.resolved.bg },
  failed: { text: "Не смогли", bg: "bg-destructive" },
}

/** Список остановок по порядку: адрес или категория, время, статус. */
function StopList({
  data,
  activeId,
}: {
  data: MyRoute
  activeId: string | null
}) {
  const jobById = new Map(data.jobs.map((j) => [j.id, j]))
  const clusterById = new Map(data.clusters.map((c) => [c.id, c]))
  const describe = (job: Job | undefined) => {
    const c = job ? clusterById.get(job.cluster_ids[0]) : undefined
    return {
      category: c?.category ?? "",
      address:
        job?.cluster_ids
          .map((id) => clusterById.get(id)?.address)
          .find(Boolean) ?? null,
      count: job?.cluster_ids.length ?? 1,
    }
  }
  return (
    <ol
      className="divide-y rounded-2xl border bg-card"
      aria-label="Все остановки"
    >
      {data.route.stops.map((s, i) => {
        const d = describe(jobById.get(s.job_id))
        const label = STOP_LABEL[s.status]
        return (
          <li
            key={s.job_id}
            className={cn(
              "flex items-center gap-3 px-4 py-3",
              s.job_id === activeId && "bg-accent/60",
            )}
          >
            <span className="w-5 text-sm text-muted-foreground tabular-nums">
              {i + 1}
            </span>
            <CategoryIcon
              category={d.category}
              className="size-5 shrink-0 text-muted-foreground"
            />
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-2 text-base">
                <span className="truncate">
                  {categoryInfo(d.category).label}
                </span>
                {d.count > 1 && (
                  <span
                    className="shrink-0 rounded-full bg-muted px-2 text-xs text-muted-foreground tabular-nums"
                    title={`${d.count} проблемы одним выездом`}
                  >
                    ×{d.count}
                  </span>
                )}
              </p>
              <p className="truncate text-sm text-muted-foreground">
                {d.address ?? "Адрес не указан"}
              </p>
            </div>
            <div className="flex flex-col items-end gap-1">
              <span className="text-sm tabular-nums">
                {formatTime(s.arrival)}
              </span>
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <span
                  className={cn("size-2 rounded-full", label.bg)}
                  aria-hidden
                />
                {label.text}
              </span>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

/** Экран бригады: карта, следующая остановка крупно, действия, весь маршрут. */
export function CrewRouteScreen() {
  const { user } = useAuth()
  const crewId = user?.crew_id ?? (USE_MOCK ? "c1" : "")
  const { data, isPending, error, refetch } = useMyRoute(crewId)
  const update = useJobUpdate()

  // Баннер «Маршрут обновлён» при смене версии утверждённого плана.
  const seenVersion = useRef<number | null>(null)
  const [updated, setUpdated] = useState(false)
  useEffect(() => {
    const v = data?.version ?? null
    if (routeChanged(seenVersion.current, v)) setUpdated(true)
    if (v !== null) seenVersion.current = v
  }, [data?.version])
  useEffect(() => {
    if (!updated) return
    const t = setTimeout(() => setUpdated(false), 8000)
    return () => clearTimeout(t)
  }, [updated])

  const stop = nextStop(data?.route)
  const job = stop ? data?.jobs.find((j) => j.id === stop.job_id) : undefined
  const doneCount =
    data?.route.stops.filter((s) => s.status === "done").length ?? 0

  let body: React.ReactNode
  if (isPending) body = <Skeleton rows={4} />
  else if (error)
    body = (
      <ErrorState
        title="Маршрут не загрузился"
        error={error}
        onRetry={() => refetch()}
      />
    )
  else if (!data)
    body = (
      <EmptyState
        icon={ClipboardList}
        title="План ещё не утверждён"
        hint="Руководитель отправит маршрут, экран обновится сам."
        action={
          USE_MOCK && (
            <Button
              variant="outline"
              size="lg"
              className="h-12"
              onClick={() => {
                const draft = selectDraft(getMockState())
                if (draft) approvePlan(draft.id)
              }}
            >
              Демо: утвердить план v1
            </Button>
          )
        }
      />
    )
  else
    body = (
      <>
        {updated && (
          <div
            role="status"
            className="flex items-center gap-2 rounded-xl bg-primary px-4 py-3 text-base text-primary-foreground"
          >
            <RefreshCw className="size-5" aria-hidden />
            Маршрут обновлён: план v{data.version}
          </div>
        )}
        {stop && job ? (
          <>
            <NextStopCard stop={stop} job={job} clusters={data.clusters} />
            <StopActions
              stop={stop}
              crewId={crewId}
              onUpdate={(u) => update.mutate(u)}
              busy={update.isPending}
            />
          </>
        ) : (
          <EmptyState
            title="Все остановки закрыты"
            hint={`Сделано ${doneCount} из ${data.route.stops.length}. Хорошая смена.`}
          />
        )}
        <div>
          <p className="mb-2 px-1 text-sm text-muted-foreground">
            Маршрут на сегодня · {data.route.stops.length} остановок ·{" "}
            {data.route.drive_min} мин в пути
          </p>
          <StopList data={data} activeId={stop?.job_id ?? null} />
        </div>
      </>
    )

  return (
    <div className="-m-6 md:-m-8" data-testid="crew-screen">
      <CityMap
        className="h-[40vh] min-h-56 w-full"
        layers={data ? [{ kind: "crew", route: data.route }] : []}
      />
      <div className="mx-auto flex w-full max-w-md flex-col gap-4 p-4 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
        {body}
      </div>
    </div>
  )
}
