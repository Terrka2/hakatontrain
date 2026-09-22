// Данные экрана бригады. Единственное место, где фича знает про mock и про API.
import { client } from "@/client/client.gen"
import { apiGet, USE_MOCK } from "@/lib/api"
import type { ClusterOut, CrewRoute, Job, JobUpdate } from "@/lib/contracts"
import {
  getMockState,
  later,
  selectApproved,
  submitJobUpdate,
} from "@/lib/mock-store"

/** Мой маршрут на сегодня: только из утверждённого плана. null — плана ещё нет. */
export type MyRoute = {
  plan_id: string
  version: number
  route: CrewRoute
  jobs: Job[]
  clusters: ClusterOut[]
}

export async function fetchMyRoute(crewId: string): Promise<MyRoute | null> {
  if (USE_MOCK) {
    const state = getMockState()
    const plan = selectApproved(state)
    const route = plan?.routes.find((r) => r.crew_id === crewId)
    if (!plan || !route) return later(null)
    const jobIds = new Set(route.stops.map((s) => s.job_id))
    const jobs = plan.jobs.filter((j) => jobIds.has(j.id))
    const clusterIds = new Set(jobs.flatMap((j) => j.cluster_ids))
    return later({
      plan_id: plan.id,
      version: plan.version,
      route,
      jobs,
      clusters: state.items.filter((c) => clusterIds.has(c.id)),
    })
  }
  return apiGet<MyRoute | null>("/api/v1/crew/me/route")
}

export async function postJobUpdate(update: JobUpdate): Promise<void> {
  if (USE_MOCK) {
    submitJobUpdate(update)
    return later(undefined)
  }
  await client.post({
    url: `/api/v1/crew/jobs/${update.job_id}/status`,
    body: update,
    throwOnError: true,
  })
}
