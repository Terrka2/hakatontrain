import { createFileRoute } from "@tanstack/react-router"

import { QueueScreen } from "@/features/queue"

export const Route = createFileRoute("/_layout/queue")({
  component: QueueScreen,
  head: () => ({ meta: [{ title: "Очередь приоритетов — CityTriage" }] }),
})
