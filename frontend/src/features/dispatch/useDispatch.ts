import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { USE_MOCK } from "@/lib/api"
import type { WeatherMode } from "@/lib/mock-city"
import { useMockCity } from "@/lib/mock-store"
import {
  approve,
  fetchApproved,
  fetchCrews,
  fetchDraft,
  fetchRuns,
  resetAll,
  switchWeather,
} from "./api"

const POLL_MS = 5000

/** В mock-режиме ключ меняется с часами демо, поэтому любое действие сразу перечитывает данные. */
function useTick(): string {
  const { clock } = useMockCity()
  return USE_MOCK ? clock : "api"
}

export function useRuns() {
  const tick = useTick()
  return useQuery({
    queryKey: ["operator-runs", tick],
    queryFn: fetchRuns,
    refetchInterval: POLL_MS,
  })
}

export function useDraft() {
  const tick = useTick()
  return useQuery({
    queryKey: ["plan", "draft", tick],
    queryFn: fetchDraft,
    refetchInterval: POLL_MS,
  })
}

export function useApproved() {
  const tick = useTick()
  return useQuery({
    queryKey: ["plan", "approved", tick],
    queryFn: fetchApproved,
    refetchInterval: POLL_MS,
  })
}

export function useCrews() {
  return useQuery({
    queryKey: ["crews"],
    queryFn: fetchCrews,
    staleTime: 60_000,
  })
}

export function useDispatchActions() {
  const qc = useQueryClient()
  const invalidate = () => qc.invalidateQueries()
  const approveMut = useMutation({ mutationFn: approve, onSuccess: invalidate })
  const weatherMut = useMutation({
    mutationFn: (m: WeatherMode) => switchWeather(m),
    onSuccess: invalidate,
  })
  const resetMut = useMutation({ mutationFn: resetAll, onSuccess: invalidate })
  return { approveMut, weatherMut, resetMut }
}
