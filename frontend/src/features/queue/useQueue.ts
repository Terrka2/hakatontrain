import { useQuery } from "@tanstack/react-query"

import { USE_MOCK } from "@/lib/api"
import { useMockCity } from "@/lib/mock-store"
import { fetchQueue, fetchReports } from "./api"

/** В mock-режиме часы стора входят в ключ: после действий оператора очередь перечитывается. */
function mockKey(clock: string): string {
  return USE_MOCK ? clock : "api"
}

export function useQueue() {
  const { clock } = useMockCity()
  return useQuery({
    queryKey: ["clusters", mockKey(clock)],
    queryFn: fetchQueue,
    staleTime: 30_000,
  })
}

export function useReports() {
  const { clock } = useMockCity()
  return useQuery({
    queryKey: ["reports", mockKey(clock)],
    queryFn: fetchReports,
    staleTime: 30_000,
  })
}
