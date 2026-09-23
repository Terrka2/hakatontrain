import { CategoryIcon } from "@/components/ui/CategoryIcon"
import { PriorityBadge } from "@/components/ui/PriorityBadge"
import type { ClusterOut, Crew, Job, Plan, StopStatus } from "@/lib/contracts"
import { cn } from "@/lib/utils"
import { categoryInfo } from "@/theme/categories"
import { crewColor } from "@/theme/priority"
import { fmtTime, stopLabel } from "./diff"

const STOP_RU: Record<StopStatus, string> = {
  pending: "ожидает",
  arrived: "на месте",
  done: "сделано",
  failed: "не смогли",
}
const STOP_DOT: Record<StopStatus, string> = {
  pending: "bg-status-open",
  arrived: "bg-status-in-progress",
  done: "bg-status-resolved",
  failed: "bg-priority-high",
}

function tripsWord(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return "выезд"
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "выезда"
  return "выездов"
}

type Props = { plan: Plan; crews: Crew[]; clusters?: ClusterOut[] }

/** Колонки по бригадам: остановки по порядку, время, статус. */
export function PlanView({ plan, crews, clusters = [] }: Props) {
  const jobs = new Map<string, Job>(plan.jobs.map((j) => [j.id, j]))
  const byCluster = new Map(clusters.map((c) => [c.id, c]))
  const order = crews.map((c) => c.id)
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {plan.routes.map((route) => {
        const crew = crews.find((c) => c.id === route.crew_id)
        const color = crewColor(Math.max(0, order.indexOf(route.crew_id)))
        return (
          <section
            key={route.crew_id}
            className="min-w-0 overflow-hidden rounded-xl border"
            aria-label={crew?.name ?? route.crew_id}
          >
            <header className="flex items-center gap-2 border-b px-3 py-2">
              <span
                className={cn("size-3 rounded-full", color.bg)}
                aria-hidden
              />
              <h3 className="min-w-0 flex-1 truncate text-sm font-semibold">
                {crew?.name ?? route.crew_id}
              </h3>
              <span className="text-xs text-muted-foreground tabular-nums">
                {route.stops.length} {tripsWord(route.stops.length)} ·{" "}
                {route.drive_min + route.work_min} мин
              </span>
            </header>
            {route.stops.length === 0 ? (
              <p className="px-3 py-4 text-sm text-muted-foreground">
                Выездов нет
              </p>
            ) : (
              <ol className="divide-y">
                {route.stops.map((stop, i) => {
                  const job = jobs.get(stop.job_id)
                  const first = job
                    ? byCluster.get(job.cluster_ids[0])
                    : undefined
                  return (
                    <li key={stop.job_id} className="flex gap-3 px-3 py-2.5">
                      <span className="mt-0.5 w-5 shrink-0 text-center text-xs text-muted-foreground tabular-nums">
                        {i + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          {first && (
                            <CategoryIcon
                              category={first.category}
                              className="size-4 shrink-0 text-muted-foreground"
                            />
                          )}
                          <span className="truncate text-sm font-medium">
                            {first
                              ? categoryInfo(first.category).label
                              : (job?.skill ?? stop.job_id)}
                          </span>
                          {job && (
                            <PriorityBadge
                              score={job.priority}
                              compact
                              className="ml-auto"
                            />
                          )}
                        </div>
                        <p className="truncate text-xs text-muted-foreground">
                          {first?.address ?? first?.summary ?? stop.job_id}
                        </p>
                        <p className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground tabular-nums">
                          <span>
                            {fmtTime(stop.arrival)}–{fmtTime(stop.departure)}
                          </span>
                          {job && <span>{stopLabel(job)}</span>}
                          <span className="flex items-center gap-1">
                            <span
                              className={cn(
                                "size-2 rounded-full",
                                STOP_DOT[stop.status],
                              )}
                              aria-hidden
                            />
                            {STOP_RU[stop.status]}
                          </span>
                        </p>
                      </div>
                    </li>
                  )
                })}
              </ol>
            )}
          </section>
        )
      })}
      {plan.unassigned.length > 0 && (
        <p className="text-sm text-muted-foreground md:col-span-3">
          Не распределено: {plan.unassigned.join(", ")}
        </p>
      )}
    </div>
  )
}
