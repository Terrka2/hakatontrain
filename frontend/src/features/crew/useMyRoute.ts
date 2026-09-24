import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { USE_MOCK } from "@/lib/api"
import type { JobUpdate } from "@/lib/contracts"
import { useMockCity } from "@/lib/mock-store"
import { fetchMyRoute, postJobUpdate } from "./api"

/** Маршрут опрашивается каждые 10 с; в mock-режиме ключ меняется с каждым событием «города». */
export function useMyRoute(crewId: string) {
  const { clock } = useMockCity()
  return useQuery({
    queryKey: ["crew-route", crewId, USE_MOCK ? clock : "api"],
    queryFn: () => fetchMyRoute(crewId),
    refetchInterval: 10_000,
  })
}

export function useJobUpdate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (u: JobUpdate) => postJobUpdate(u),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crew-route"] }),
  })
}
