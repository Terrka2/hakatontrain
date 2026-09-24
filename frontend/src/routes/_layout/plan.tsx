import { createFileRoute } from "@tanstack/react-router"

import { DispatchScreen } from "@/features/dispatch"

export const Route = createFileRoute("/_layout/plan")({
  component: DispatchScreen,
  head: () => ({ meta: [{ title: "План и бригады — CityTriage" }] }),
})
