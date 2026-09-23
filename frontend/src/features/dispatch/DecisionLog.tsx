import { EmptyState } from "@/components/ui/EmptyState"
import type { Decision } from "@/lib/contracts"
import { cn } from "@/lib/utils"
import { DECISION_RU } from "./diff"

const TONE: Record<Decision["kind"], string> = {
  defer: "bg-priority-mid text-priority-mid-foreground",
  boost: "bg-priority-high text-priority-high-foreground",
  batch: "bg-primary text-primary-foreground",
  deadline: "bg-primary text-primary-foreground",
  unassigned: "bg-destructive text-primary-foreground",
  param: "bg-muted text-muted-foreground",
  replan: "bg-priority-low text-priority-low-foreground",
  review: "bg-muted text-foreground",
}

const BY_RU: Record<Decision["by"], string> = {
  rule: "правило",
  llm: "ИИ",
  operator: "человек",
}

/** Журнал решений оператора: что и почему изменило план. */
export function DecisionLog({ decisions }: { decisions: Decision[] }) {
  if (!decisions.length)
    return (
      <EmptyState
        title="Решений нет"
        hint="Оператор ничего не менял в этом плане."
        className="min-h-24"
      />
    )
  return (
    <ul className="flex flex-col gap-2" aria-label="Журнал решений">
      {decisions.map((d, i) => (
        <li
          key={`${d.kind}-${d.subject_id}-${i}`}
          className="flex items-start gap-2 text-sm"
        >
          <span
            className={cn(
              "mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
              TONE[d.kind],
            )}
          >
            {DECISION_RU[d.kind]}
          </span>
          <span className="min-w-0">
            <span className="font-mono text-xs text-muted-foreground">
              {d.subject_id}
            </span>{" "}
            {d.reason}
            <span className="text-xs text-muted-foreground">
              {" "}
              · {BY_RU[d.by]}
            </span>
          </span>
        </li>
      ))}
    </ul>
  )
}
