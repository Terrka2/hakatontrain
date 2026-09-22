import { Send } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { Plan } from "@/lib/contracts"

type Props = {
  draft: Plan
  onApprove: () => void
  canApprove?: boolean
  busy?: boolean
}

/** Одна кнопка человека: утвердить черновик и отправить бригадам. ИИ её нажать не может. */
export function ApproveBar({
  draft,
  onApprove,
  canApprove = true,
  busy = false,
}: Props) {
  const stops = draft.routes.reduce((s, r) => s + r.stops.length, 0)
  return (
    <div
      className="flex flex-wrap items-center gap-3 rounded-xl border bg-card p-3"
      data-testid="approve-bar"
    >
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">Черновик плана v{draft.version}</p>
        <p className="text-xs text-muted-foreground tabular-nums">
          {stops} выездов · {draft.routes.length} бригады · собран оператором,
          ждёт вашего решения
        </p>
      </div>
      <Button
        size="lg"
        className="min-h-12 w-full sm:w-auto"
        onClick={onApprove}
        disabled={!canApprove || busy}
        title={
          canApprove ? undefined : "Утверждать план может только руководитель"
        }
      >
        <Send aria-hidden />
        Утвердить и отправить бригадам
      </Button>
    </div>
  )
}
