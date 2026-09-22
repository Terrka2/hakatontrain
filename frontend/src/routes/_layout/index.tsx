import { createFileRoute } from "@tanstack/react-router"

import { BlockPlaceholder } from "@/components/Common/BlockPlaceholder"

export const Route = createFileRoute("/_layout/")({
  component: MapScreen,
  head: () => ({ meta: [{ title: "Карта — CityTriage" }] }),
})

function MapScreen() {
  return <BlockPlaceholder block="F1" title="Карта" contract="F1_map.md" />
}
