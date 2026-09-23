import type { Factor } from "@/lib/contracts"
import { cn } from "@/lib/utils"
import { segmentColor, segments } from "./bar"

type Props = { factors: Factor[]; score: number }

/** Полоса приоритета: сегмент на фактор, ширина = вклад. Ниже — что именно дало баллы. */
export function PriorityBar({ factors, score }: Props) {
  const segs = segments(factors, score)
  return (
    <div className="flex flex-col gap-2" data-testid="priority-bar">
      <div className="flex items-baseline justify-between">
        <span className="text-sm text-muted-foreground">
          Из чего сложился балл
        </span>
        <span className="text-2xl font-semibold tabular-nums">
          {Math.round(score)}
        </span>
      </div>
      <div
        className="flex h-3 w-full overflow-hidden rounded-full bg-muted"
        role="img"
        aria-label={`Балл ${Math.round(score)}`}
      >
        {segs
          .filter((s) => s.width > 0)
          .map((s) => (
            <div
              key={s.code}
              title={`${s.label}: +${s.points}`}
              style={{ width: `${s.width}%` }}
              className={cn("h-full", segmentColor(s.code))}
            />
          ))}
      </div>
      <ul className="flex flex-col gap-1 text-sm">
        {segs.map((s) => (
          <li
            key={s.code}
            className={cn(
              "flex items-start gap-2",
              s.noData && "text-muted-foreground",
            )}
          >
            <span
              className={cn(
                "mt-1.5 size-2 shrink-0 rounded-full",
                s.noData ? "bg-muted-foreground/40" : segmentColor(s.code),
              )}
              aria-hidden
            />
            <span className="w-10 shrink-0 font-medium tabular-nums">
              {s.noData ? "—" : `+${s.points}`}
            </span>
            <span className="min-w-0">
              <span className="font-medium">{s.label}</span>
              {s.noData ? (
                <span className="text-muted-foreground"> — нет данных</span>
              ) : s.evidence ? (
                <span className="text-muted-foreground"> — {s.evidence}</span>
              ) : null}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
