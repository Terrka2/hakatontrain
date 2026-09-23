import { CategoryIcon } from "@/components/ui/CategoryIcon"
import { PriorityBadge } from "@/components/ui/PriorityBadge"
import type { ClusterOut } from "@/lib/contracts"
import { cn } from "@/lib/utils"
import { categoryInfo } from "@/theme/categories"

type Props = {
  items: ClusterOut[]
  selectedId?: string
  onSelect: (id: string) => void
}

/** Очередь: сверху то, что чинить первым. Строка — кнопка, чтобы тап работал и с клавиатуры. */
export function PriorityQueue({ items, selectedId, onSelect }: Props) {
  return (
    <ol
      className="flex flex-col"
      aria-label="Очередь приоритетов"
      data-testid="priority-queue"
    >
      {items.map((c, i) => {
        const selected = c.id === selectedId
        return (
          <li key={c.id}>
            <button
              type="button"
              onClick={() => onSelect(c.id)}
              aria-current={selected ? "true" : undefined}
              data-cluster-row={c.id}
              className={cn(
                "flex min-h-14 w-full items-center gap-3 border-b px-3 py-2 text-left transition-colors",
                "hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                selected && "bg-accent",
              )}
            >
              <span className="w-5 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
                {i + 1}
              </span>
              <CategoryIcon
                category={c.category}
                className="size-5 shrink-0 text-muted-foreground"
              />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">
                  {categoryInfo(c.category).label}
                </span>
                <span className="block truncate text-xs text-muted-foreground">
                  {c.address ?? c.summary}
                  {c.report_ids.length > 1
                    ? ` · ${c.report_ids.length} обращения`
                    : ""}
                </span>
              </span>
              <PriorityBadge
                score={c.score}
                needsReview={c.needs_review}
                compact
              />
            </button>
          </li>
        )
      })}
    </ol>
  )
}
