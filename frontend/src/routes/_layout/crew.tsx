import { createFileRoute } from "@tanstack/react-router"

import { CrewRouteScreen } from "@/features/crew"

export const Route = createFileRoute("/_layout/crew")({
  component: CrewRouteScreen,
  head: () => ({ meta: [{ title: "Мой маршрут — CityTriage" }] }),
})
