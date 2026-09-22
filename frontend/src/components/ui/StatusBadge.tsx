/**
 * F6 · StatusBadge — бейдж статуса заявки.
 * Цвета берутся только из theme/priority.ts (токены F6).
 * Без запросов к API, без состояния.
 */

import * as React from "react"
import { cn } from "@/lib/utils"
import { STATUS_COLORS } from "@/theme/priority"

export type ReportStatus = "open" | "in_progress" | "done" | "rejected"

interface StatusBadgeProps extends React.ComponentProps<"span"> {
  status: ReportStatus
}

/**
 * Отображает бейдж статуса заявки с цветовым кодированием.
 * Поддерживает светлую и тёмную тему автоматически.
 *
 * @example
 * <StatusBadge status="open" />        // Открыта
 * <StatusBadge status="in_progress" /> // В работе
 * <StatusBadge status="done" />        // Выполнена
 * <StatusBadge status="rejected" />    // Отклонена
 */
function StatusBadge({ status, className, ...props }: StatusBadgeProps) {
  const config = STATUS_COLORS[status]

  if (!config) {
    // неизвестный статус — нейтральный серый
    return (
      <span
        data-slot="status-badge"
        data-status={status}
        className={cn(
          "inline-flex items-center gap-1 rounded-full px-2 py-0.5",
          "text-xs font-semibold leading-none whitespace-nowrap",
          "border border-transparent",
          "bg-muted text-muted-foreground",
          className,
        )}
        aria-label={`Статус: ${status}`}
        {...props}
      >
        {status}
      </span>
    )
  }

  return (
    <span
      data-slot="status-badge"
      data-status={status}
      style={
        {
          "--badge-bg": config.light.bg,
          "--badge-text": config.light.text,
          "--badge-bg-dark": config.dark.bg,
          "--badge-text-dark": config.dark.text,
          backgroundColor: "var(--badge-bg)",
          color: "var(--badge-text)",
        } as React.CSSProperties
      }
      className={cn(
        // layout
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5",
        // typography
        "text-xs font-semibold leading-none whitespace-nowrap",
        // shape
        "border border-transparent",
        // dark-mode override
        "dark:bg-[var(--badge-bg-dark)] dark:text-[var(--badge-text-dark)]",
        className,
      )}
      aria-label={`Статус: ${config.label}`}
      {...props}
    >
      {config.label}
    </span>
  )
}

export { StatusBadge }

