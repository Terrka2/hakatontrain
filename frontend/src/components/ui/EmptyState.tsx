import { Inbox, type LucideIcon } from "lucide-react"
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

type Props = {
  title: string
  hint?: string
  icon?: LucideIcon
  action?: ReactNode
  className?: string
}

/** Пустой экран — приглашение к действию, а не извинение. */
export function EmptyState({ title, hint, icon: Icon = Inbox, action, className }: Props) {
  return (
    <div
      role="status"
      className={cn("flex min-h-40 flex-col items-center justify-center gap-2 px-4 py-8 text-center", className)}
    >
      <Icon className="size-8 text-muted-foreground" aria-hidden />
      <p className="text-base font-medium">{title}</p>
      {hint && <p className="max-w-prose text-sm text-muted-foreground">{hint}</p>}
      {action && <div className="pt-2">{action}</div>}
    </div>
  )
}
