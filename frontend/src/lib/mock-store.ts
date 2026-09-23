// Состояние mock-«города» на время сессии: погода, планы, лента оператора, сообщения бригад.
// Единственное место, где mock изменяется. Экраны читают через useMockCity() / async-функции api.
import { useSyncExternalStore } from "react"

import demoJson from "@/mocks/demo_city.json"
import type {
  AssistantRequest,
  AssistantResponse,
  ClusterOut,
  DemoCity,
  JobUpdate,
  OperatorRun,
  Plan,
  Report,
} from "./contracts.ts"
import {
  applyJobUpdate,
  buildPlan,
  clusterOuts,
  mockAssistantReply,
  runSummary,
  type WeatherMode,
} from "./mock-city.ts"

export const demo = demoJson as unknown as DemoCity

export type MockState = {
  weather: WeatherMode
  items: ClusterOut[]
  reports: Report[]
  plans: Plan[]
  runs: OperatorRun[]
  updates: JobUpdate[]
  /** Мировое время демо: fixture.now плюс прошедшие события. */
  clock: string
}

function tick(state: MockState, min: number): string {
  return new Date(new Date(state.clock).getTime() + min * 60_000).toISOString()
}

function initial(weather: WeatherMode = "clear"): MockState {
  const { items, reports } = clusterOuts(demo, demo.weather[weather])
  const plan = buildPlan(items, demo, weather, 1)
  const runBase = {
    id: "run-1",
    trigger: "import" as const,
    at: demo.now,
    reports_seen: reports.length,
    clusters_total: items.length,
    clusters_new: items.length,
    needs_review: items.filter((c) => c.needs_review).map((c) => c.id),
    plan_id: plan.id,
    decisions: plan.decisions,
  }
  return {
    weather,
    items,
    reports,
    plans: [plan],
    runs: [{ ...runBase, summary: runSummary(runBase, plan) }],
    updates: [],
    clock: demo.now,
  }
}

let state: MockState = initial()
const listeners = new Set<() => void>()
function set(next: MockState) {
  state = next
  for (const l of listeners) l()
}
function subscribe(l: () => void) {
  listeners.add(l)
  return () => listeners.delete(l)
}
export function getMockState(): MockState {
  return state
}
export function useMockCity(): MockState {
  return useSyncExternalStore(subscribe, getMockState, getMockState)
}

export const selectDraft = (s: MockState): Plan | null =>
  s.plans.filter((p) => p.status === "draft").slice(-1)[0] ?? null
export const selectApproved = (s: MockState): Plan | null =>
  s.plans.filter((p) => p.status === "approved").slice(-1)[0] ?? null

/** Небольшая задержка, чтобы состояния загрузки были видны и на mock. */
export function later<T>(value: T, ms = 120): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms))
}

// ---------- действия ----------

export function resetDemo(): void {
  set(initial())
}

/** Перестройка плана оператором: новый черновик v+1 и запись в ленту. */
function replan(
  s: MockState,
  trigger: OperatorRun["trigger"],
  extra: Plan["decisions"],
  excludeJobIds: string[],
  skillOverrides: Record<string, string> = {},
): MockState {
  const { items } = clusterOuts(demo, demo.weather[s.weather])
  const version = Math.max(...s.plans.map((p) => p.version)) + 1
  const plan = buildPlan(
    items,
    demo,
    s.weather,
    version,
    extra,
    excludeJobIds,
    skillOverrides,
  )
  const approved = selectApproved(s)
  // Уже отмеченные бригадой остановки переносятся в новый черновик как есть.
  if (approved) {
    plan.routes = plan.routes.map((r) => {
      const prev = approved.routes.find((p) => p.crew_id === r.crew_id)
      return prev
        ? {
            ...r,
            stops: r.stops.map((st) => ({
              ...st,
              status:
                prev.stops.find((p) => p.job_id === st.job_id)?.status ??
                "pending",
            })),
          }
        : r
    })
  }
  const clock = tick(s, 3)
  const runBase = {
    id: `run-${s.runs.length + 1}`,
    trigger,
    at: clock,
    reports_seen: s.reports.length,
    clusters_total: items.length,
    clusters_new: 0,
    needs_review: items.filter((c) => c.needs_review).map((c) => c.id),
    plan_id: plan.id,
    decisions: plan.decisions,
  }
  const plans = s.plans
    .map((p) =>
      p.status === "draft" ? { ...p, status: "superseded" as const } : p,
    )
    .concat(plan)
  return {
    ...s,
    items,
    plans,
    runs: [...s.runs, { ...runBase, summary: runSummary(runBase, plan) }],
    clock,
  }
}

export function setWeather(weather: WeatherMode): void {
  if (weather === state.weather) return
  const next = { ...state, weather }
  set(
    replan(
      next,
      "weather",
      [
        {
          kind: "param",
          subject_id: "weather",
          reason:
            weather === "storm"
              ? "Погода: шторм (ливень 12 мм, ветер 17 м/с)"
              : "Погода: ясно",
          by: "operator",
        },
      ],
      [],
    ),
  )
}

export function approvePlan(
  planId: string,
  by = "supervisor@demo.md",
): Plan | null {
  const plan = state.plans.find((p) => p.id === planId)
  if (plan?.status !== "draft") return null
  const plans = state.plans.map((p) =>
    p.id === planId
      ? { ...p, status: "approved" as const, approved_by: by }
      : p.status === "approved"
        ? { ...p, status: "superseded" as const }
        : p,
  )
  set({ ...state, plans, clock: tick(state, 1) })
  return plans.find((p) => p.id === planId) ?? null
}

/** Сообщение бригады с выезда. «Не могу» запускает перестройку: задание уходит другой бригаде или в нераспределённые. */
export function submitJobUpdate(update: JobUpdate): void {
  const approved = selectApproved(state)
  if (!approved) return
  const plans = state.plans.map((p) =>
    p.id === approved.id ? applyJobUpdate(p, update) : p,
  )
  let next: MockState = {
    ...state,
    plans,
    updates: [...state.updates, update],
    clock: tick(state, 1),
  }
  if (update.status === "failed") {
    const reasonText: Record<NonNullable<JobUpdate["reason"]>, string> = {
      no_access: "нет доступа к месту",
      needs_other_skill: `нужна другая бригада (${update.needs_skill ?? "?"})`,
      not_found: "проблему на месте не нашли",
      weather: "погода не позволяет",
      other: update.note || "другая причина",
    }
    const extra: Plan["decisions"] = [
      {
        kind: "replan",
        subject_id: update.job_id,
        reason: `Бригада ${update.crew_id}: ${reasonText[update.reason ?? "other"]} — план перестроен`,
        by: "rule",
      },
    ]
    const done = approved.routes.flatMap((r) =>
      r.stops
        .filter((s) => s.status === "done" || s.status === "arrived")
        .map((s) => s.job_id),
    )
    const job = approved.jobs.find((j) => j.id === update.job_id)
    const overrides =
      job && update.reason === "needs_other_skill" && update.needs_skill
        ? { [job.id]: update.needs_skill }
        : {}
    // Задание с новым навыком уйдёт другой бригаде; остальные причины — задание в нераспределённые.
    next = replan(
      next,
      "job_update",
      extra,
      overrides[update.job_id] ? done : [...done, update.job_id],
      overrides,
    )
  }
  set(next)
}

export function askAssistant(req: AssistantRequest): AssistantResponse {
  const reply = mockAssistantReply(req, {
    items: state.items,
    runs: state.runs,
    draft: selectDraft(state),
    weather: state.weather,
  })
  for (const a of reply.actions)
    if (a.kind === "set_filter" && typeof a.payload.weather === "string")
      setWeather(a.payload.weather as WeatherMode)
  return reply
}

export function confirmPending(pendingId: string): AssistantResponse {
  const planId = pendingId.replace(/^pending-/, "")
  const plan = approvePlan(planId)
  return {
    text: plan
      ? `План v${plan.version} утверждён и отправлен бригадам.`
      : "Этот черновик уже не актуален.",
    actions: plan ? [{ kind: "show_plan", payload: { plan_id: plan.id } }] : [],
    pending: null,
    trace: ["tool:approve_plan"],
  }
}
