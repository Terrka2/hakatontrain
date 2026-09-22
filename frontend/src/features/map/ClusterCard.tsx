import { X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { CategoryIcon } from "@/components/ui/CategoryIcon"
import { PriorityBadge } from "@/components/ui/PriorityBadge"
import { StatusBadge } from "@/components/ui/StatusBadge"
import { categoryInfo } from "@/theme/categories"
import type { ClusterOut } from "./types"

type Props = { cluster: ClusterOut; onClose: () => void }

function reportsWord(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return "обращение"
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20))
    return "обращения"
  return "обращений"
}

/** Карточка выбранного кластера: что, где, насколько срочно. */
export function ClusterCard({ cluster, onClose }: Props) {
  const count = cluster.report_ids.length
  return (
    <article className="flex flex-col gap-3" aria-label="Выбранная проблема">
      <div className="flex items-start gap-3">
        <CategoryIcon
          category={cluster.category}
          className="mt-0.5 size-6 shrink-0 text-muted-foreground"
        />
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold leading-tight">
            {categoryInfo(cluster.category).label}
          </h2>
          <p className="truncate text-sm text-muted-foreground">
            {cluster.address ?? "Адрес не указан"}
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="-mr-2 -mt-2 size-12 shrink-0"
          aria-label="Закрыть"
          onClick={onClose}
        >
          <X className="size-5" />
        </Button>
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <PriorityBadge
          score={cluster.score}
          needsReview={cluster.needs_review}
        />
        <StatusBadge status={cluster.status} />
        <span className="text-xs text-muted-foreground tabular-nums">
          {count} {reportsWord(count)}
        </span>
      </div>
      <p className="text-sm leading-relaxed">{cluster.summary}</p>
      {cluster.needs_review && (
        <p className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
          Текст похож на сгенерированный или без деталей. Перед выездом нужна
          проверка.
        </p>
      )}
    </article>
  )
}
