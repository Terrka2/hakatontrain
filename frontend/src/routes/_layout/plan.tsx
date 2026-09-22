import { createFileRoute } from "@tanstack/react-router"

import { BlockPlaceholder } from "@/components/Common/BlockPlaceholder"

export const Route = createFileRoute("/_layout/plan")({
  component: PlanScreen,
  head: () => ({ meta: [{ title: "План и бригады — CityTriage" }] }),
})

function PlanScreen() {
  return (
    <BlockPlaceholder
      block="F3"
      title="План и бригады"
      contract="F3_dispatch-ui.md"
    />
  )
}
