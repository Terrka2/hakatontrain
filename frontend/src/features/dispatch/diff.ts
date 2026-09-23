// Чистая логика пульта: сравнение планов, подписи. Тестируется node --test, без алиасов и React.
import type { Decision, Job, OperatorRun, Plan } from "../../lib/contracts.ts"

export type PlanDiffResult = {
  added: string[]
  removed: string[]
  moved: { job_id: string; from: string; to: string }[]
}

/** Карта job_id → бригада по маршрутам плана. */
export function assignments(plan: Plan): Map<string, string> {
  const m = new Map<string, string>()
  for (const r of plan.routes)
    for (const s of r.stops) m.set(s.job_id, r.crew_id)
  return m
}

/** Что изменилось между текущим планом и черновиком: только сравнение двух Plan по job_id. */
export function planDiff(current: Plan | null, draft: Plan): PlanDiffResult {
  const next = assignments(draft)
  if (!current) return { added: [...next.keys()], removed: [], moved: [] }
  const prev = assignments(current)
  const added = [...next.keys()].filter((id) => !prev.has(id))
  const removed = [...prev.keys()].filter((id) => !next.has(id))
  const moved = [...next.entries()]
    .filter(([id, crew]) => prev.has(id) && prev.get(id) !== crew)
    .map(([id, to]) => ({ job_id: id, from: prev.get(id) as string, to }))
  return { added, removed, moved }
}

export function problemsWord(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return "проблема"
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20))
    return "проблемы"
  return "проблем"
}

/** «4 проблемы · 1 выезд» для остановки с несколькими кластерами, иначе «1 проблема». */
export function stopLabel(job: Job): string {
  const n = job.cluster_ids.length
  return n > 1 ? `${n} ${problemsWord(n)} · 1 выезд` : "1 проблема"
}

export const TRIGGER_RU: Record<OperatorRun["trigger"], string> = {
  import: "импорт",
  new_report: "новое обращение",
  job_update: "сообщение бригады",
  weather: "погода",
  manual: "вручную",
}

export const DECISION_RU: Record<Decision["kind"], string> = {
  defer: "отложено",
  boost: "поднято",
  batch: "объединено",
  deadline: "к сроку",
  unassigned: "не влезло",
  param: "параметр",
  replan: "перестроено",
  review: "на проверку",
}

export function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Chisinau",
  })
}

export function planVersion(planId: string | null): number | null {
  const m = /(\d+)$/.exec(planId ?? "")
  return m ? Number(m[1]) : null
}

/** «07:02 · импорт · 16 обращений → 13 проблем, 1 на проверку, план v1». */
export function feedLine(run: OperatorRun): string {
  const parts = [
    `${run.reports_seen} обращений → ${run.clusters_total} проблем`,
  ]
  if (run.needs_review.length)
    parts.push(`${run.needs_review.length} на проверку`)
  const v = planVersion(run.plan_id)
  if (v !== null) parts.push(`план v${v}`)
  return `${fmtTime(run.at)} · ${TRIGGER_RU[run.trigger]} · ${parts.join(", ")}`
}

/** Насколько план лучше обработки по очереди, в процентах (null, если базы нет). */
export function gainPercent(total: number, baseline: number): number | null {
  if (baseline <= 0) return null
  return Math.round(((total - baseline) / baseline) * 100)
}
