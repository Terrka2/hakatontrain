import { createFileRoute } from "@tanstack/react-router"

import { BlockPlaceholder } from "@/components/Common/BlockPlaceholder"

export const Route = createFileRoute("/_layout/crew")({
  component: CrewScreen,
  head: () => ({ meta: [{ title: "Мой маршрут — CityTriage" }] }),
})

function CrewScreen() {
  return (
    <BlockPlaceholder block="F5" title="Мой маршрут" contract="F5_crew.md" />
  )
}
