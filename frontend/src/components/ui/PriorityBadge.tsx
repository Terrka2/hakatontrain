/**
 * F6 · PriorityBadge — бейдж приоритета заявки.
 * Цвета берутся только из theme/priority.ts (токены F6).
 * Без запросов к API, без состояния.
 */

import * as React from "react"
import { cn } from "@/lib/utils"
import { PRIORITY_BADGES } from "@/theme/priority"

export type PriorityLevel = "high" | "medium" | "low"

interface PriorityBadgeProps extends React.ComponentProps<"span"> {
  priority: PriorityLevel
}

/**
 * Отображает бейдж приоритета с цветовым кодированием (WCAG AA ≥ 4.5:1).
 * Автоматически переключает цветовую схему в зависимости от .dark-класса на родителе.
 *
 * @example
 * <PriorityBadge priority="high" />   // Высокий
 * <PriorityBadge priority="medium" /> // Средний
 * <PriorityBadge priority="low" />    // Низкий
 */
function PriorityBadge({ priority, className, ...props }: PriorityBadgeProps) {
  const config = PRIORITY_BADGES[priority]

  return (
    <span
      data-slot="priority-badge"
      data-priority={priority}
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
        // dark-mode override via Tailwind dark: prefix
        "dark:[--badge-bg:var(--badge-bg-dark)] dark:[--badge-text:var(--badge-text-dark)]",
        "dark:bg-[var(--badge-bg-dark)] dark:text-[var(--badge-text-dark)]",
        className,
      )}
      aria-label={`Приоритет: ${config.label}`}
      {...props}
    >
      {config.label}
    </span>
  )
}

export { PriorityBadge }

