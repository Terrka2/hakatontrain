import { createFileRoute } from "@tanstack/react-router"

import { MapScreen } from "@/features/map"

export const Route = createFileRoute("/_layout/")({
  component: MapScreen,
  head: () => ({ meta: [{ title: "Карта — CityTriage" }] }),
})
