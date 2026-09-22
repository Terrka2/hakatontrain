import { Navigation } from "lucide-react"

import { Button } from "@/components/ui/button"
import { CategoryIcon } from "@/components/ui/CategoryIcon"
import type { ClusterOut, Job, RouteStop } from "@/lib/contracts"
import { categoryInfo } from "@/theme/categories"
import { formatTime, geoLink } from "./logic"

type Props = { stop: RouteStop; job: Job; clusters?: ClusterOut[] }

function problemsWord(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return "проблема"
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20))
    return "проблемы"
  return "проблем"
}

/** Следующая остановка крупно: что сделать, где, во сколько, кнопка в навигатор. */
export function NextStopCard({ stop, job, clusters = [] }: Props) {
  const own = clusters.filter((c) => job.cluster_ids.includes(c.id))
  const first = own[0]
  const category = first?.category ?? ""
  const address = own.find((c) => c.address)?.address ?? null
  const count = job.cluster_ids.length
  const arrived = stop.status === "arrived"

  return (
    <section
      aria-label="Следующая остановка"
      className="rounded-2xl border bg-card p-4 text-card-foreground shadow-sm"
    >
      <p className="text-sm text-muted-foreground">
        {arrived ? "Вы на месте" : `Следующая · к ${formatTime(stop.arrival)}`}
      </p>
      <div className="mt-1 flex items-start gap-3">
        <CategoryIcon
          category={category}
          className="mt-1 size-8 shrink-0 text-primary"
        />
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl font-semibold leading-tight">
            {categoryInfo(category).label}
          </h2>
          <p className="mt-1 text-base leading-snug">
            {address ??
              `${job.location.lat.toFixed(4)}, ${job.location.lon.toFixed(4)}`}
          </p>
          <p className="mt-1 text-sm text-muted-foreground tabular-nums">
            {count > 1
              ? `${count} ${problemsWord(count)} · 1 выезд`
              : "1 проблема"}{" "}
            · {job.service_min} мин работы
          </p>
        </div>
      </div>
      {first?.summary && (
        <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-muted-foreground">
          {first.summary}
        </p>
      )}
      <Button
        asChild
        variant="outline"
        size="lg"
        className="mt-4 h-12 w-full text-base"
      >
        <a href={geoLink(job.location)}>
          <Navigation className="size-5" aria-hidden />
          Открыть в навигаторе
        </a>
      </Button>
    </section>
  )
}
