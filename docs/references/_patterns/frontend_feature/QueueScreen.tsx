import { EmptyState } from "@/components/ui/EmptyState"
import { PriorityBadge } from "@/components/ui/PriorityBadge"
import { Skeleton } from "@/components/ui/Skeleton"

import { useQueue } from "./useQueue"

export function QueueScreen() {
  const { data, isPending, error } = useQueue()
  if (isPending) return <Skeleton rows={6} />
  if (error) return <EmptyState title="Не удалось загрузить очередь" hint={String(error)} />
  if (!data?.length) return <EmptyState title="Открытых проблем нет" />

  return (
    <ul className="divide-y">
      {data.map((c) => (
        <li key={c.id} className="flex items-center justify-between gap-3 py-3">
          <span className="font-mono text-sm text-muted-foreground">{c.id}</span>
          <span className="flex-1 truncate">{c.category}</span>
          <PriorityBadge score={c.score} needsReview={c.needs_review} />
        </li>
      ))}
    </ul>
  )
}
