// L0-«город»: единый источник mock-данных для всех экранов при VITE_USE_MOCK=true.
// Повторяет формулы контрактов B3/B4/B6 на fixture, чтобы цифры совпадали с бэкендом, когда он появится.
// Чистые функции внизу тестируются node --test; стор — в mock-store.ts.
import {
  type AssistantRequest,
  type AssistantResponse,
  CATEGORY_SERVICE_MIN,
  CATEGORY_TO_SKILL,
  type Cluster,
  type ClusterOut,
  type Crew,
  type CrewRoute,
  type Decision,
  type DemoCity,
  type Factor,
  type GeoPoint,
  type Job,
  type JobUpdate,
  type OperatorRun,
  type Plan,
  type Priority,
  type Report,
  type RouteStop,
  type Weather,
} from "./contracts.ts"

export type WeatherMode = "clear" | "storm"

// ---------- гео ----------

export function distanceM(a: GeoPoint, b: GeoPoint): number {
  const dLat = (b.lat - a.lat) * 111_320
  const dLon =
    (b.lon - a.lon) *
    111_320 *
    Math.cos(((a.lat + b.lat) / 2) * (Math.PI / 180))
  return Math.hypot(dLat, dLon)
}

function centroid(points: GeoPoint[]): GeoPoint {
  const n = points.length
  return {
    lat: points.reduce((s, p) => s + p.lat, 0) / n,
    lon: points.reduce((s, p) => s + p.lon, 0) / n,
  }
}

// ---------- обращения: то, что сделал бы L1 (extract/verify) ----------

/** Fixture → Report с обогащением L1 на минимуме: suspicious для expect.suspicious_report. */
export function reportsFromDemo(demo: DemoCity): Report[] {
  return demo.reports.map((r) => ({
    ...r,
    source: r.source ?? "dataset",
    lang: r.lang ?? null,
    cluster_id: null,
    extracted: null,
    verification:
      r.id === demo.expect.suspicious_report
        ? {
            status: "suspicious",
            reasons: [
              "Обращение без адреса и деталей",
              "Текст похож на сгенерированный",
              "Нет фото и подтверждений",
            ],
            confidence: 0.2,
          }
        : null,
  }))
}

// ---------- кластеры (B3 на fixture) ----------

export function clustersFromReports(
  reports: Report[],
  demo: DemoCity,
): Cluster[] {
  const open = reports.filter((r) => r.status === "open")
  const trio = new Set(demo.expect.dup_trio)
  const groups: Report[][] = []
  const trioGroup = open.filter((r) => trio.has(r.id))
  if (trioGroup.length) groups.push(trioGroup)
  for (const r of open) if (!trio.has(r.id)) groups.push([r])
  return groups.map((rs) => {
    const first = rs
      .slice()
      .sort((a, b) => a.created_at.localeCompare(b.created_at))
    const links =
      rs.length > 1
        ? rs.slice(1).map((r) => ({
            a: rs[0].id,
            b: r.id,
            distance_m: Math.round(distanceM(rs[0].location, r.location)),
            text_sim: 0.71,
          }))
        : []
    return {
      id: `cl-${first[0].id}`,
      category: rs[0].category,
      centroid: centroid(rs.map((r) => r.location)),
      report_ids: rs.map((r) => r.id),
      links,
      first_reported_at: first[0].created_at,
      last_reported_at: first[first.length - 1].created_at,
      status: "open",
    }
  })
}

// ---------- приоритет (B4 на fixture) ----------

const WEIGHTS: Record<string, number> = {
  HZ: 0.25,
  DM: 0.15,
  AG: 0.15,
  SP: 0.15,
  RC: 0.1,
  EX: 0.1,
  WX: 0.05,
  VF: 0.05,
}
const LABELS: Record<string, string> = {
  HZ: "Опасность",
  DM: "Спрос",
  AG: "Возраст",
  SP: "Соц. объекты",
  RC: "Повтор",
  EX: "Мероприятие",
  WX: "Погода",
  VF: "Достоверность",
}
const HZ_BASE: Record<string, number> = {
  manhole: 0.9,
  tree: 0.7,
  water_leak: 0.6,
  pothole: 0.5,
  traffic_sign: 0.5,
  streetlight: 0.4,
  garbage: 0.2,
  public_space: 0.1,
}
const HZ_SIGNALS =
  /(упал|упала|травм|пострада|нет крышки|крышки нет|скорая|дтп|căzut|rănit|accident)/i

type Ctx = {
  now: Date
  weather: Weather | null
  infrastructure: DemoCity["infrastructure"]
  history: Report[]
}

function evalFactors(
  cluster: Cluster,
  reports: Report[],
  ctx: Ctx,
): Record<string, [number | null, string[]]> {
  const base = HZ_BASE[cluster.category] ?? 0.1
  const signal = reports.find((r) => HZ_SIGNALS.test(r.text))
  const hz = Math.min(1, base + (signal ? 0.2 : 0))
  const hzEv = [
    `Категория «${cluster.category}»: базовая опасность ${base.toFixed(1)}`,
  ]
  if (signal) hzEv.push(`Слова-сигналы в обращении ${signal.id} (+0.2)`)

  const conf = reports.reduce((s, r) => s + r.confirmations, 0)
  const dm = Math.min(1, (reports.length + conf) / 10)

  const days = Math.max(
    0,
    (ctx.now.getTime() - new Date(cluster.first_reported_at).getTime()) /
      86_400_000,
  )
  const ag = Math.min(1, days / 14)

  let sp: number | null = null
  const spEv: string[] = []
  if (ctx.infrastructure.length) {
    const social = ctx.infrastructure.filter((i) => i.kind !== "stop")
    const nearest = social
      .map((i) => ({ i, d: distanceM(cluster.centroid, i.location) }))
      .sort((a, b) => a.d - b.d)[0]
    sp = nearest && nearest.d <= 150 ? 1 : nearest && nearest.d <= 300 ? 0.5 : 0
    if (nearest && sp > 0)
      spEv.push(`${nearest.i.name} в ${Math.round(nearest.d)} м`)
  }

  let rc: number | null = null
  const rcEv: string[] = []
  if (ctx.history.length) {
    const hit = ctx.history.find(
      (h) =>
        h.status === "resolved" &&
        h.category === cluster.category &&
        distanceM(cluster.centroid, h.location) <= 60 &&
        new Date(cluster.first_reported_at).getTime() -
          new Date(h.created_at).getTime() <=
          366 * 86_400_000,
    )
    rc = hit ? 1 : 0
    if (hit)
      rcEv.push(
        `Уже чинили: обращение ${hit.id} в ${Math.round(distanceM(cluster.centroid, hit.location))} м, закрыто ${hit.created_at.slice(0, 10)}`,
      )
  }

  let wx: number | null = null
  const wxEv: string[] = []
  if (ctx.weather) {
    wx = 0
    if (cluster.category === "tree" && ctx.weather.wind_ms >= 15) {
      wx = 1
      wxEv.push(`Ветер ${ctx.weather.wind_ms} м/с: ветки опасны`)
    }
    if (cluster.category === "water_leak" && ctx.weather.temp_c <= 0) {
      wx = 1
      wxEv.push(`Мороз ${ctx.weather.temp_c}°C: наледь`)
    }
  }

  const verified = reports.filter(
    (r) =>
      r.photo_url ||
      (r.verification &&
        ["plausible", "confirmed"].includes(r.verification.status)),
  ).length
  const vf = verified / reports.length

  return {
    HZ: [hz, hzEv],
    DM: [dm, [`Обращений: ${reports.length}, подтверждений: ${conf}`]],
    AG: [ag, [`Первое обращение ${Math.round(days)} дн. назад`]],
    SP: [sp, spEv],
    RC: [rc, rcEv],
    EX: [null, []],
    WX: [wx, wxEv],
    VF: [
      vf,
      vf > 0
        ? [`С фото или подтверждено: ${verified} из ${reports.length}`]
        : [],
    ],
  }
}

export function priorityOf(
  cluster: Cluster,
  reports: Report[],
  ctx: Ctx,
): Priority {
  const ev = evalFactors(cluster, reports, ctx)
  const total = Object.values(WEIGHTS).reduce((s, w) => s + w, 0)
  const valid = Object.entries(WEIGHTS)
    .filter(([c]) => ev[c][0] !== null)
    .reduce((s, [, w]) => s + w, 0)
  const raw =
    (100 *
      Object.entries(WEIGHTS).reduce(
        (s, [c, w]) => s + (ev[c][0] ?? 0) * w,
        0,
      )) /
    valid
  const factors: Factor[] = Object.entries(WEIGHTS).map(([code, weight]) => ({
    code,
    label: LABELS[code],
    score: ev[code][0],
    weight,
    points:
      ev[code][0] === null
        ? 0
        : Math.round(((100 * weight * (ev[code][0] as number)) / valid) * 10) /
          10,
    evidence: ev[code][1],
  }))
  let score = Math.round(raw * 10) / 10
  if ((ev.HZ[0] ?? 0) >= 0.9 && score < 80) {
    factors.push({
      code: "FL",
      label: "Аварийный минимум",
      score: 1,
      weight: 0,
      points: Math.round((80 - score) * 10) / 10,
      evidence: ["Опасность ≥ 0.9: балл не ниже 80"],
    })
    score = 80
  }
  const confidence = Math.round((valid / total) * 100) / 100
  return {
    cluster_id: cluster.id,
    score,
    factors,
    confidence,
    needs_review:
      confidence < 0.5 ||
      reports.some((r) => r.verification?.status === "suspicious"),
  }
}

export function clusterOuts(
  demo: DemoCity,
  weather: Weather | null,
): { items: ClusterOut[]; reports: Report[] } {
  const reports = reportsFromDemo(demo)
  const byId = new Map(reports.map((r) => [r.id, r]))
  const ctx: Ctx = {
    now: new Date(demo.now),
    weather,
    infrastructure: demo.infrastructure,
    history: reports.filter((r) => r.status === "resolved"),
  }
  const items = clustersFromReports(reports, demo)
    .map((c): ClusterOut => {
      const rs = c.report_ids.map((id) => byId.get(id) as Report)
      const priority = priorityOf(c, rs, ctx)
      return {
        ...c,
        score: priority.score,
        needs_review: priority.needs_review,
        priority,
        address: rs.find((r) => r.address)?.address ?? null,
        summary: rs[0].text,
      }
    })
    .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id))
  return { items, reports }
}

// ---------- план (B6 greedy на fixture) ----------

const SPEED_KMH = 25

function addMin(iso: string, min: number): string {
  return new Date(new Date(iso).getTime() + min * 60_000).toISOString()
}

export function jobsFromClusters(
  items: ClusterOut[],
  demo: DemoCity,
  weather: WeatherMode,
): { jobs: Job[]; decisions: Decision[] } {
  const decisions: Decision[] = []
  const usable = items.filter((c) => !c.needs_review)
  for (const c of items.filter((c) => c.needs_review))
    decisions.push({
      kind: "review",
      subject_id: c.id,
      reason: "Обращение помечено как сомнительное — ждёт решения руководителя",
      by: "rule",
    })
  const batchIds = new Set(demo.expect.site_batch.map((id) => `cl-${id}`))
  const batch = usable.filter((c) => batchIds.has(c.id))
  const rest = usable.filter((c) => !batchIds.has(c.id))
  const jobs: Job[] = rest.map((c) => ({
    id: `job-${c.id.slice(3)}`,
    cluster_ids: [c.id],
    location: c.centroid,
    skill: CATEGORY_TO_SKILL[c.category] ?? "road",
    service_min: CATEGORY_SERVICE_MIN[c.category] ?? 30,
    priority: Math.round(c.score),
    deadline: null,
  }))
  if (batch.length) {
    jobs.push({
      id: `job-${batch[0].id.slice(3)}-site`,
      cluster_ids: batch.map((c) => c.id),
      location: centroid(batch.map((c) => c.centroid)),
      skill: "road",
      service_min: Math.round(
        batch.reduce(
          (s, c) => s + (CATEGORY_SERVICE_MIN[c.category] ?? 30),
          0,
        ) * 0.6,
      ),
      priority: Math.max(...batch.map((c) => Math.round(c.score))),
      deadline: null,
    })
    decisions.push({
      kind: "batch",
      subject_id: jobs[jobs.length - 1].id,
      reason: `${batch.length} проблемы на ${batch[0].address?.split(",")[0] ?? "одной улице"} объединены в один выезд`,
      by: "rule",
    })
  }
  if (weather === "storm") {
    const catOf = (j: Job) =>
      items.find((c) => c.id === j.cluster_ids[0])?.category
    for (const j of jobs) {
      const cat = catOf(j)
      if (cat && demo.expect.storm_defers_categories.includes(cat))
        decisions.push({
          kind: "defer",
          subject_id: j.id,
          reason:
            "Ливень: ямы под водой, ремонт асфальта невозможен — отложено до ясной погоды",
          by: "rule",
        })
      if (cat && demo.expect.storm_boosts_categories.includes(cat)) {
        j.priority = Math.min(100, j.priority + 20)
        decisions.push({
          kind: "boost",
          subject_id: j.id,
          reason: "Ветер 17 м/с: аварийные ветки — приоритет поднят",
          by: "rule",
        })
      }
    }
    const deferred = new Set(
      decisions.filter((d) => d.kind === "defer").map((d) => d.subject_id),
    )
    return { jobs: jobs.filter((j) => !deferred.has(j.id)), decisions }
  }
  return { jobs, decisions }
}

export function buildRoutes(
  jobs: Job[],
  crews: Crew[],
): { routes: CrewRoute[]; unassigned: string[] } {
  const free = new Set(jobs.map((j) => j.id))
  const byId = new Map(jobs.map((j) => [j.id, j]))
  const routes: CrewRoute[] = []
  for (const crew of crews) {
    let at = crew.start
    let clock = crew.shift_start
    let drive = 0
    let work = 0
    const stops: RouteStop[] = []
    for (;;) {
      const candidates = [...free]
        .map((id) => byId.get(id) as Job)
        .filter((j) => crew.skills.includes(j.skill))
      if (!candidates.length) break
      const pick = candidates
        .map((j) => ({ j, d: distanceM(at, j.location) }))
        .sort(
          (a, b) =>
            b.j.priority - a.j.priority - (b.d - a.d) / 200 || a.d - b.d,
        )[0]
      const driveMin = Math.round((pick.d / 1000 / SPEED_KMH) * 60)
      const arrival = addMin(clock, driveMin)
      const departure = addMin(arrival, pick.j.service_min)
      if (new Date(departure) > new Date(crew.shift_end)) break
      stops.push({
        job_id: pick.j.id,
        location: pick.j.location,
        arrival,
        departure,
        status: "pending",
      })
      free.delete(pick.j.id)
      drive += driveMin
      work += pick.j.service_min
      at = pick.j.location
      clock = departure
    }
    routes.push({
      crew_id: crew.id,
      stops,
      geometry: [crew.start, ...stops.map((s) => s.location)],
      drive_min: drive,
      work_min: work,
    })
  }
  return { routes, unassigned: [...free] }
}

/** «Ценность» плана: приоритет × доля смены, оставшаяся на момент приезда. Раньше высокий приоритет — больше. */
function planValue(routes: CrewRoute[], jobs: Job[], crews: Crew[]): number {
  const jobById = new Map(jobs.map((j) => [j.id, j]))
  let total = 0
  for (const r of routes) {
    const crew = crews.find((c) => c.id === r.crew_id)
    if (!crew) continue
    const start = new Date(crew.shift_start).getTime()
    const len = new Date(crew.shift_end).getTime() - start
    for (const s of r.stops) {
      const j = jobById.get(s.job_id)
      if (j)
        total +=
          j.priority * (1 - (new Date(s.arrival).getTime() - start) / len)
    }
  }
  return Math.round(total)
}

export function buildPlan(
  items: ClusterOut[],
  demo: DemoCity,
  weather: WeatherMode,
  version: number,
  extra: Decision[] = [],
  excludeJobIds: string[] = [],
  skillOverrides: Record<string, string> = {},
): Plan {
  const { jobs: allJobs, decisions } = jobsFromClusters(items, demo, weather)
  const jobs = allJobs
    .filter((j) => !excludeJobIds.includes(j.id))
    .map((j) =>
      skillOverrides[j.id] ? { ...j, skill: skillOverrides[j.id] } : j,
    )
  const { routes, unassigned } = buildRoutes(jobs, demo.crews)
  const fifo = jobs.slice().sort((a, b) => {
    const fa =
      items.find((c) => c.id === a.cluster_ids[0])?.first_reported_at ?? ""
    const fb =
      items.find((c) => c.id === b.cluster_ids[0])?.first_reported_at ?? ""
    return fa.localeCompare(fb)
  })
  const baseline = buildRoutes(
    fifo.map((j) => ({ ...j, priority: 1 })),
    demo.crews,
  ).routes
  for (const id of unassigned)
    decisions.push({
      kind: "unassigned",
      subject_id: id,
      reason: "Не помещается в смену ни одной бригады с нужным навыком",
      by: "rule",
    })
  return {
    id: `plan-${version}`,
    day: demo.now.slice(0, 10),
    routes,
    unassigned,
    total_priority: planValue(routes, jobs, demo.crews),
    baseline_total_priority: planValue(baseline, jobs, demo.crews),
    decisions: [...extra, ...decisions],
    engine: "greedy",
    status: "draft",
    version,
    approved_by: null,
    jobs,
  }
}

// ---------- лента оператора ----------

export function runSummary(
  run: Omit<OperatorRun, "summary">,
  plan: Plan | null,
): string {
  const what: Record<OperatorRun["trigger"], string> = {
    import: "Импорт обращений",
    new_report: "Новое обращение",
    job_update: "Сообщение бригады",
    weather: "Смена погоды",
    manual: "Запуск вручную",
  }
  const parts = [
    `${what[run.trigger]}: ${run.reports_seen} обращений → ${run.clusters_total} проблем`,
  ]
  if (run.clusters_new) parts.push(`${run.clusters_new} новых`)
  if (run.needs_review.length)
    parts.push(`${run.needs_review.length} на проверку`)
  if (plan)
    parts.push(
      `план v${plan.version}, ${plan.routes.reduce((s, r) => s + r.stops.length, 0)} выездов`,
    )
  return parts.join(", ")
}

// ---------- ассистент (L2 без LLM: интенты по ключевым словам) ----------

export type AssistantCtx = {
  items: ClusterOut[]
  runs: OperatorRun[]
  draft: Plan | null
  weather: WeatherMode
}

export function mockAssistantReply(
  req: AssistantRequest,
  ctx: AssistantCtx,
): AssistantResponse {
  const m = req.message.toLowerCase()
  const top = ctx.items[0]
  const selected =
    ctx.items.find((c) => c.id === req.ui_state.selected_cluster_id) ?? null
  if (/что ты сделал|что сделал|отчит|лента/.test(m)) {
    const last = ctx.runs[ctx.runs.length - 1]
    return {
      text: last
        ? `${last.summary}. Решения: ${last.decisions.length}, из них ${last.decisions.filter((d) => d.kind === "review").length} ждут вас.`
        : "Я ещё ничего не делал: нажмите «Сброс демо» или импортируйте обращения.",
      actions: last ? [{ kind: "show_run", payload: { run_id: last.id } }] : [],
      pending: null,
      trace: ["intent:explain_run", "tool:list_runs"],
    }
  }
  if (/почему|why|объясни/.test(m)) {
    const c = selected ?? top
    if (!c)
      return {
        text: "На карте пока нет проблем.",
        actions: [],
        pending: null,
        trace: ["intent:explain_priority"],
      }
    const lines = c.priority.factors
      .filter((f) => f.score !== null && f.points > 0)
      .sort((a, b) => b.points - a.points)
      .map(
        (f) =>
          `+${f.points} ${f.label}${f.evidence[0] ? ` — ${f.evidence[0]}` : ""}`,
      )
    return {
      text: `${selected ? "Выбранная проблема" : "Первая в очереди"} — ${c.id}, балл ${c.score}. ${lines.join("; ")}.`,
      actions: [{ kind: "focus_cluster", payload: { cluster_id: c.id } }],
      pending: null,
      trace: ["intent:explain_priority", "tool:get_priority"],
    }
  }
  if (/ливень|дожд|шторм|гроза|storm|ураган/.test(m)) {
    return {
      text: "Переключаю погоду на шторм: ямы откладываю до ясной погоды, аварийные ветки поднимаю выше. Собираю новый черновик плана.",
      actions: [
        { kind: "set_filter", payload: { weather: "storm" } },
        { kind: "show_plan", payload: {} },
      ],
      pending: null,
      trace: ["intent:weather_change", "tool:set_weather", "tool:solve"],
    }
  }
  if (/ясно|распогод|солнц|clear/.test(m)) {
    return {
      text: "Погода ясная: возвращаю ямы в план.",
      actions: [
        { kind: "set_filter", payload: { weather: "clear" } },
        { kind: "show_plan", payload: {} },
      ],
      pending: null,
      trace: ["intent:weather_change", "tool:set_weather", "tool:solve"],
    }
  }
  if (/утверд|approve|отправ/.test(m)) {
    if (!ctx.draft)
      return {
        text: "Черновика плана нет — утверждать нечего.",
        actions: [],
        pending: null,
        trace: ["intent:approve_plan"],
      }
    return {
      text: `Готов отправить бригадам план v${ctx.draft.version}: ${ctx.draft.routes.reduce((s, r) => s + r.stops.length, 0)} выездов. Утверждать план может только руководитель — подтвердите.`,
      actions: [{ kind: "show_plan", payload: { plan_id: ctx.draft.id } }],
      pending: {
        id: `pending-${ctx.draft.id}`,
        tool: "approve_plan",
        args: { plan_id: ctx.draft.id },
        summary: `Утвердить план v${ctx.draft.version} и отправить его трём бригадам`,
      },
      trace: ["intent:approve_plan", "guard:human_only"],
    }
  }
  if (/план|маршрут/.test(m)) {
    return {
      text: ctx.draft
        ? `Черновик v${ctx.draft.version}: ${ctx.draft.routes.map((r) => `${r.crew_id} — ${r.stops.length} выездов`).join(", ")}.`
        : "Плана пока нет.",
      actions: [{ kind: "show_plan", payload: {} }],
      pending: null,
      trace: ["intent:show_plan"],
    }
  }
  return {
    text: "Я ИИ-оператор. Спросите: «Что ты сделал?», «Почему это первое?», скажите «Пошёл ливень» или «Утверди план».",
    actions: [],
    pending: null,
    trace: ["intent:unknown"],
  }
}

export function applyJobUpdate(plan: Plan, update: JobUpdate): Plan {
  return {
    ...plan,
    routes: plan.routes.map((r) =>
      r.crew_id !== update.crew_id
        ? r
        : {
            ...r,
            stops: r.stops.map((s) =>
              s.job_id === update.job_id ? { ...s, status: update.status } : s,
            ),
          },
    ),
  }
}
