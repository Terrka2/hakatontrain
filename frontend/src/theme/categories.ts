// Блок F6 · категории обращений: подпись RU и имя иконки (lucide). Иконку рисует components/ui/CategoryIcon.
// Контракт: docs/contracts/F6_design.md

export type CategoryIconName =
  | "construction"
  | "lightbulb"
  | "circle-dashed"
  | "trash"
  | "tree"
  | "droplets"
  | "armchair"
  | "help"

export type CategoryInfo = { label: string; icon: CategoryIconName }

export const CATEGORIES: Record<string, CategoryInfo> = {
  pothole: { label: "Яма на дороге", icon: "construction" },
  streetlight: { label: "Не горит фонарь", icon: "lightbulb" },
  manhole: { label: "Открытый люк", icon: "circle-dashed" },
  garbage: { label: "Мусор", icon: "trash" },
  tree: { label: "Аварийное дерево", icon: "tree" },
  water_leak: { label: "Утечка воды", icon: "droplets" },
  public_space: { label: "Благоустройство", icon: "armchair" },
}

const UNKNOWN: CategoryInfo = { label: "Другое", icon: "help" }

/** Категория из данных может прийти в любом регистре и с пробелами. */
export function categoryInfo(
  category: string | null | undefined,
): CategoryInfo {
  const key = (category ?? "").trim().toLowerCase()
  return CATEGORIES[key] ?? UNKNOWN
}
