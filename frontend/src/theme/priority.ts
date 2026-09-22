/**
 * F6 · Дизайн-система — единственный источник цветов для F1–F5.
 * Контракт: docs/contracts/F6_design.md
 *
 * Экспортирует:
 *   PRIORITY_BADGES  — цвета бейджей приоритета (контраст ≥ 4.5:1 в обеих темах)
 *   CREW_COLORS      — цвета бригад
 *   STATUS_COLORS    — цвета статусов заявок
 *   CATEGORY_CONFIG  — иконки и RU-подписи категорий (резервный экспорт;
 *                      основной компонент — CategoryIcon в components/ui)
 */

import {
  AlertTriangle,
  CircleDashed,
  Droplets,
  Lamp,
  Leaf,
  Package,
  Trash2,
  TreePine,
  type LucideIcon,
} from "lucide-react"

// ─── Типы ─────────────────────────────────────────────────────────────────

export interface ThemePair {
  /** Цвет фона бейджа */
  bg: string
  /** Цвет текста бейджа (WCAG ≥ 4.5:1 к bg) */
  text: string
}

export interface PriorityLevel {
  light: ThemePair
  dark: ThemePair
  /** Человекочитаемое название на русском */
  label: string
  /** Числовой вес (higher = важнее) */
  weight: number
}

export interface CrewColor {
  light: ThemePair
  dark: ThemePair
  label: string
}

export interface StatusColor {
  light: ThemePair
  dark: ThemePair
  label: string
}

export interface CategoryEntry {
  label: string
  icon: LucideIcon
}

// ─── Приоритеты ───────────────────────────────────────────────────────────
// Светлая тема: тёмный фон + белый текст (контраст 7–8.5:1)
// Тёмная тема:  светлый пастельный фон + очень тёмный текст (контраст 8.5–10:1)

export const PRIORITY_BADGES: Record<"high" | "medium" | "low", PriorityLevel> = {
  high: {
    light: { bg: "#991B1B", text: "#FFFFFF" }, // 8.31:1
    dark:  { bg: "#FCA5A5", text: "#3B0000" }, // 9.33:1
    label: "Высокий",
    weight: 3,
  },
  medium: {
    light: { bg: "#92400E", text: "#FFFFFF" }, // 7.09:1
    dark:  { bg: "#FED7AA", text: "#5C2D00" }, // 8.48:1
    label: "Средний",
    weight: 2,
  },
  low: {
    light: { bg: "#166534", text: "#FFFFFF" }, // 7.13:1
    dark:  { bg: "#BBF7D0", text: "#0F3D1E" }, // 10.15:1
    label: "Низкий",
    weight: 1,
  },
}

// ─── Бригады ──────────────────────────────────────────────────────────────

export const CREW_COLORS: Record<string, CrewColor> = {
  alpha: {
    light: { bg: "#1E3A8A", text: "#FFFFFF" },
    dark:  { bg: "#BFDBFE", text: "#1E3A8A" },
    label: "Альфа",
  },
  beta: {
    light: { bg: "#5B21B6", text: "#FFFFFF" },
    dark:  { bg: "#DDD6FE", text: "#3B0764" },
    label: "Бета",
  },
  gamma: {
    light: { bg: "#065F46", text: "#FFFFFF" },
    dark:  { bg: "#A7F3D0", text: "#022C22" },
    label: "Гамма",
  },
}

// ─── Статусы заявок ───────────────────────────────────────────────────────

export const STATUS_COLORS: Record<string, StatusColor> = {
  open: {
    light: { bg: "#1E40AF", text: "#FFFFFF" },
    dark:  { bg: "#BFDBFE", text: "#1E3A8A" },
    label: "Открыта",
  },
  in_progress: {
    light: { bg: "#92400E", text: "#FFFFFF" },
    dark:  { bg: "#FED7AA", text: "#5C2D00" },
    label: "В работе",
  },
  done: {
    light: { bg: "#166534", text: "#FFFFFF" },
    dark:  { bg: "#BBF7D0", text: "#0F3D1E" },
    label: "Выполнена",
  },
  rejected: {
    light: { bg: "#374151", text: "#FFFFFF" },
    dark:  { bg: "#E5E7EB", text: "#111827" },
    label: "Отклонена",
  },
}

// ─── Категории ────────────────────────────────────────────────────────────
// Источник категорий: backend/app/fixtures/demo_city.json
// Основной компонент: frontend/src/components/ui/CategoryIcon.tsx (задача F6-4)

export const CATEGORY_CONFIG: Record<string, CategoryEntry> = {
  pothole: {
    label: "Яма",
    icon: AlertTriangle,
  },
  streetlight: {
    label: "Освещение",
    icon: Lamp,
  },
  public_space: {
    label: "Общественное пространство",
    icon: Package,
  },
  manhole: {
    label: "Люк",
    icon: CircleDashed,
  },
  garbage: {
    label: "Мусор",
    icon: Trash2,
  },
  tree: {
    label: "Дерево",
    icon: TreePine,
  },
  water_leak: {
    label: "Течь воды",
    icon: Droplets,
  },
  // дополнительная — на случай расширения фикстуры
  traffic_sign: {
    label: "Знак",
    icon: Leaf,
  },
}
