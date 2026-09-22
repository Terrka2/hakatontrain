import { createFileRoute } from "@tanstack/react-router"

import { BlockPlaceholder } from "@/components/Common/BlockPlaceholder"

export const Route = createFileRoute("/_layout/queue")({
  component: QueueScreen,
  head: () => ({ meta: [{ title: "Очередь приоритетов — CityTriage" }] }),
})

function QueueScreen() {
  return (
    <BlockPlaceholder
      block="F2"
      title="Очередь приоритетов"
      contract="F2_queue.md"
    />
  )
}
