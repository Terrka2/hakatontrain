// Блок F6 · цвета приоритета, бригад и статусов. Единственное место, откуда их берут F1–F5.
// Контракт: docs/contracts/F6_design.md
// Сами значения живут в src/index.css (светлая и тёмная тема); здесь — только имена токенов.

export type PriorityLevel = "high" | "mid" | "low"
export type ClusterStatus = "open" | "planned" | "in_progress" | "resolved"

/** Границы ступеней. Согласованы с fixture: manhole ≥ 80 и яма у школы ≥ 70 → high; «шум» ≤ 30 → low. */
export const PRIORITY_THRESHOLDS = { high: 70, mid: 40 } as const

export function priorityLevel(score: number): PriorityLevel {
  if (score >= PRIORITY_THRESHOLDS.high) return "high"
  if (score >= PRIORITY_THRESHOLDS.mid) return "mid"
  return "low"
}

type Token = {
  label: string
  /** CSS-переменная для inline-стилей и карты: `var(--priority-high)`. */
  cssVar: string
  /** Tailwind-классы фона и текста. */
  bg: string
  fg: string
}

export const PRIORITY: Record<PriorityLevel, Token> = {
  high: {
    label: "Срочно",
    cssVar: "var(--priority-high)",
    bg: "bg-priority-high",
    fg: "text-priority-high-foreground",
  },
  mid: {
    label: "В очередь",
    cssVar: "var(--priority-mid)",
    bg: "bg-priority-mid",
    fg: "text-priority-mid-foreground",
  },
  low: {
    label: "Плановое",
    cssVar: "var(--priority-low)",
    bg: "bg-priority-low",
    fg: "text-priority-low-foreground",
  },
}

export const STATUS: Record<
  ClusterStatus,
  { label: string; cssVar: string; bg: string }
> = {
  open: {
    label: "Открыто",
    cssVar: "var(--status-open)",
    bg: "bg-status-open",
  },
  planned: {
    label: "В плане",
    cssVar: "var(--status-planned)",
    bg: "bg-status-planned",
  },
  in_progress: {
    label: "В работе",
    cssVar: "var(--status-in-progress)",
    bg: "bg-status-in-progress",
  },
  resolved: {
    label: "Сделано",
    cssVar: "var(--status-resolved)",
    bg: "bg-status-resolved",
  },
}

const CREW_TOKENS = [
  { cssVar: "var(--crew-1)", bg: "bg-crew-1", text: "text-crew-1" },
  { cssVar: "var(--crew-2)", bg: "bg-crew-2", text: "text-crew-2" },
  { cssVar: "var(--crew-3)", bg: "bg-crew-3", text: "text-crew-3" },
] as const

/** Цвет бригады по её порядковому номеру в плане (циклически). */
export function crewColor(index: number): (typeof CREW_TOKENS)[number] {
  const i =
    ((index % CREW_TOKENS.length) + CREW_TOKENS.length) % CREW_TOKENS.length
  return CREW_TOKENS[i]
}
