import { ShieldCheck } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { PendingAction } from "@/lib/contracts"

type Props = { pending: PendingAction; onDecide: (approve: boolean) => void }

/** Оператор предлагает действие, которое вправе сделать только человек. Ничего не уходит, пока не нажато «Подтвердить». */
export function ConfirmCard({ pending, onDecide }: Props) {
  return (
    <section
      data-testid="confirm-card"
      aria-label="Требуется подтверждение"
      className="flex flex-col gap-3 rounded-xl border-2 border-primary/60 bg-card p-4"
    >
      <div className="flex items-start gap-3">
        <ShieldCheck
          className="mt-0.5 size-5 shrink-0 text-primary"
          aria-hidden
        />
        <div className="min-w-0">
          <p className="text-sm font-semibold">Нужно ваше решение</p>
          <p className="mt-1 text-sm leading-relaxed">{pending.summary}</p>
        </div>
      </div>
      <div className="flex gap-2">
        <Button
          size="lg"
          className="min-h-12 flex-1"
          onClick={() => onDecide(true)}
        >
          Подтвердить
        </Button>
        <Button
          size="lg"
          variant="outline"
          className="min-h-12 flex-1"
          onClick={() => onDecide(false)}
        >
          Отмена
        </Button>
      </div>
    </section>
  )
}
