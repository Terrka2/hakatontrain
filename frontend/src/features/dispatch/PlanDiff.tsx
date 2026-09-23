import { ArrowRight, Minus, Plus } from "lucide-react"

import type { Plan } from "@/lib/contracts"
import { planDiff } from "./diff"

/** Что изменилось между текущим утверждённым планом и черновиком. */
export function PlanDiff({
  current,
  draft,
}: {
  current: Plan | null
  draft: Plan
}) {
  if (!current)
    return (
      <p className="text-sm text-muted-foreground">
        Первый черновик — сравнивать не с чем.
      </p>
    )
  if (current.id === draft.id)
    return (
      <p className="text-sm text-muted-foreground">
        Это утверждённый план, изменений нет.
      </p>
    )
  const d = planDiff(current, draft)
  if (!d.added.length && !d.removed.length && !d.moved.length)
    return (
      <p className="text-sm text-muted-foreground">
        Черновик v{draft.version} совпадает с планом v{current.version}.
      </p>
    )
  return (
    <ul
      className="flex flex-col gap-1.5 text-sm"
      aria-label={`Изменения черновика v${draft.version} против v${current.version}`}
    >
      {d.added.map((id) => (
        <li key={`a-${id}`} className="flex items-center gap-2">
          <Plus className="size-4 text-primary" aria-hidden />
          <span className="font-mono text-xs">{id}</span> добавлено
        </li>
      ))}
      {d.removed.map((id) => (
        <li key={`r-${id}`} className="flex items-center gap-2">
          <Minus className="size-4 text-destructive" aria-hidden />
          <span className="font-mono text-xs">{id}</span> убрано из плана
        </li>
      ))}
      {d.moved.map((m) => (
        <li key={`m-${m.job_id}`} className="flex items-center gap-2">
          <ArrowRight className="size-4 text-muted-foreground" aria-hidden />
          <span className="font-mono text-xs">{m.job_id}</span> переехало от{" "}
          {m.from} к {m.to}
        </li>
      ))}
    </ul>
  )
}
