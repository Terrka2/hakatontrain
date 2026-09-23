import { Bot } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import type { OperatorRun } from "@/lib/contracts"
import { cn } from "@/lib/utils"
import { feedLine } from "./diff"

/** Лента действий ИИ-оператора: новое сверху. */
export function OperatorFeed({ runs }: { runs: OperatorRun[] }) {
  if (!runs.length)
    return (
      <EmptyState
        icon={Bot}
        title="Оператор ещё ничего не делал"
        hint="Импортируйте обращения или нажмите «Сброс демо»."
      />
    )
  const ordered = runs.slice().reverse()
  return (
    <ol className="divide-y" aria-label="Лента оператора">
      {ordered.map((run, i) => (
        <li key={run.id} className="flex gap-3 py-3">
          <Bot
            className={cn(
              "mt-0.5 size-4 shrink-0",
              i === 0 ? "text-primary" : "text-muted-foreground",
            )}
            aria-hidden
          />
          <div className="min-w-0">
            <p className="text-sm tabular-nums">{feedLine(run)}</p>
            {run.summary && (
              <p className="text-xs text-muted-foreground">{run.summary}</p>
            )}
          </div>
        </li>
      ))}
    </ol>
  )
}
