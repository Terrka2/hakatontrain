import { gainPercent } from "./diff"

/** Сколько приоритета закрыто раньше по сравнению с обработкой по очереди. */
export function PlanVsBaseline({
  total,
  baseline,
}: {
  total: number
  baseline: number
}) {
  const gain = gainPercent(total, baseline)
  return (
    <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
      <span>
        <span className="text-2xl font-semibold tabular-nums">{total}</span>
        <span className="text-muted-foreground"> по плану</span>
      </span>
      <span className="text-muted-foreground tabular-nums">
        {baseline} по очереди поступления
      </span>
      {gain !== null && gain === 0 && (
        <span className="text-muted-foreground">
          столько же приоритета закрыто раньше, сколько при обработке по очереди
        </span>
      )}
      {gain !== null && gain !== 0 && (
        <span className={gain > 0 ? "text-primary" : "text-destructive"}>
          {gain > 0 ? `на ${gain}% больше` : `на ${-gain}% меньше`} приоритета
          закрыто раньше, чем при обработке по очереди
        </span>
      )}
    </div>
  )
}
