import { cn } from "@/lib/utils"
import { type ClusterStatus, STATUS } from "@/theme/priority"

type Props = { status: ClusterStatus | string | null | undefined; className?: string }

/** Статус кластера: точка цвета статуса + подпись. Неизвестный статус → «Открыто». */
export function StatusBadge({ status, className }: Props) {
  const key = (status ?? "open") as ClusterStatus
  const token = STATUS[key] ?? STATUS.open
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs text-muted-foreground", className)}>
      <span className={cn("size-2 rounded-full", token.bg)} aria-hidden />
      {token.label}
    </span>
  )
}
