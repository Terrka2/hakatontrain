import { AlertTriangle } from "lucide-react"

import { cn } from "@/lib/utils"
import { PRIORITY, priorityLevel } from "@/theme/priority"

type Props = {
  score: number
  needsReview?: boolean
  /** Без подписи — только цветная точка с числом (для тесных списков). */
  compact?: boolean
  className?: string
}

/** Бейдж приоритета: цвет = ступень, число = балл 0..100. needsReview → рамка и предупреждение. */
export function PriorityBadge({ score, needsReview, compact, className }: Props) {
  const level = priorityLevel(score)
  const token = PRIORITY[level]
  const rounded = Math.round(score)
  return (
    <span
      data-level={level}
      title={needsReview ? `${token.label} · требует проверки` : token.label}
      className={cn(
        "inline-flex h-6 shrink-0 items-center gap-1 rounded-full px-2 text-xs font-semibold leading-none tabular-nums",
        token.bg,
        token.fg,
        needsReview && "ring-2 ring-foreground/60 ring-offset-1 ring-offset-background",
        className,
      )}
    >
      {needsReview && <AlertTriangle className="size-3" aria-hidden />}
      <span>{rounded}</span>
      {!compact && <span className="font-medium opacity-90">{token.label}</span>}
    </span>
  )
}
