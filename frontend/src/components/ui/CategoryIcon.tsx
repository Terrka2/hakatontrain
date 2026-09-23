import {
  Armchair,
  CircleDashed,
  Construction,
  Droplets,
  HelpCircle,
  Lightbulb,
  type LucideProps,
  Trash2,
  TreeDeciduous,
} from "lucide-react"
import type { ComponentType } from "react"

import { type CategoryIconName, categoryInfo } from "@/theme/categories"

const ICONS: Record<CategoryIconName, ComponentType<LucideProps>> = {
  construction: Construction,
  lightbulb: Lightbulb,
  "circle-dashed": CircleDashed,
  trash: Trash2,
  tree: TreeDeciduous,
  droplets: Droplets,
  armchair: Armchair,
  help: HelpCircle,
}

type Props = LucideProps & { category: string | null | undefined }

/** Иконка категории обращения. Подпись RU — `categoryInfo(category).label`. */
export function CategoryIcon({ category, ...props }: Props) {
  const info = categoryInfo(category)
  const Icon = ICONS[info.icon]
  return <Icon aria-label={info.label} {...props} />
}
