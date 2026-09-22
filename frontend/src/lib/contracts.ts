// Модели контрактов (зеркало backend/app/contracts/models.py) для фронта.
// Временная замена типов сгенерированного клиента: пока B0/B6/B8 не отдают роуты в openapi.
// Поля и имена — как в Python-моделях, не переименовывать.

export type GeoPoint = { lat: number; lon: number }

export type Extracted = {
  hazard_signals: string[]
  object: string | null
  injured: boolean
  suggested_category: string | null
}

export type Verification = {
  status: "unverified" | "plausible" | "suspicious" | "confirmed"
  reasons: string[]
  confidence: number
}

export type Report = {
  id: string
  source: "dataset" | "citizen" | "voice"
  category: string
  text: string
  lang: "ro" | "ru" | "en" | null
  location: GeoPoint
  address: string | null
  photo_url: string | null
  created_at: string
  status: "open" | "in_progress" | "resolved" | "rejected"
  cluster_id: string | null
  confirmations: number
  extracted: Extracted | null
  verification: Verification | null
}

export type DupLink = {
  a: string
  b: string
  distance_m: number
  text_sim: number
}

export type ClusterStatus = "open" | "planned" | "in_progress" | "resolved"

export type Cluster = {
  id: string
  category: string
  centroid: GeoPoint
  report_ids: string[]
  links: DupLink[]
  first_reported_at: string
  last_reported_at: string
  status: ClusterStatus
}

export type Factor = {
  code: string
  label: string
  score: number | null
  weight: number
  points: number
  evidence: string[]
}

export type Priority = {
  cluster_id: string
  score: number
  factors: Factor[]
  confidence: number
  needs_review: boolean
}

/** Кластер + его приоритет: то, что отдаёт `GET /clusters?sort=priority` (B0). */
export type ClusterOut = Cluster & {
  score: number
  needs_review: boolean
  priority: Priority
  address: string | null
  summary: string
}

export type Weather = {
  at: string
  precipitation_mm: number
  wind_ms: number
  temp_c: number
  source: string
}

export type Event = {
  id: string
  title: string
  location: GeoPoint
  radius_m: number
  starts_at: string
  ends_at: string
  expected_people: number
  source: string
}

export type InfraObject = {
  id: string
  kind: "school" | "kindergarten" | "hospital" | "stop"
  name: string
  location: GeoPoint
}

export type Crew = {
  id: string
  name: string
  skills: string[]
  start: GeoPoint
  shift_start: string
  shift_end: string
}

export type Job = {
  id: string
  cluster_ids: string[]
  location: GeoPoint
  skill: string
  service_min: number
  priority: number
  deadline: string | null
}

export type DecisionKind =
  | "defer"
  | "boost"
  | "batch"
  | "deadline"
  | "unassigned"
  | "param"
  | "replan"
  | "review"

export type Decision = {
  kind: DecisionKind
  subject_id: string
  reason: string
  by: "rule" | "llm" | "operator"
}

export type StopStatus = "pending" | "arrived" | "done" | "failed"

export type RouteStop = {
  job_id: string
  location: GeoPoint
  arrival: string
  departure: string
  status: StopStatus
}

export type CrewRoute = {
  crew_id: string
  stops: RouteStop[]
  geometry: GeoPoint[]
  drive_min: number
  work_min: number
}

export type PlanStatus = "draft" | "approved" | "superseded"

export type Plan = {
  id: string
  day: string
  routes: CrewRoute[]
  unassigned: string[]
  total_priority: number
  baseline_total_priority: number
  decisions: Decision[]
  engine: string
  status: PlanStatus
  version: number
  approved_by: string | null
  /** Не из контракта: задания плана, чтобы фронт не искал их отдельно. Сервер отдаёт их в `GET /plan`. */
  jobs: Job[]
}

export type FailReason =
  | "no_access"
  | "needs_other_skill"
  | "not_found"
  | "weather"
  | "other"

export type JobUpdate = {
  job_id: string
  crew_id: string
  status: "arrived" | "done" | "failed"
  at: string
  photo_url: string | null
  reason: FailReason | null
  needs_skill: string | null
  note: string | null
}

export type OperatorRun = {
  id: string
  trigger: "import" | "new_report" | "job_update" | "weather" | "manual"
  at: string
  reports_seen: number
  clusters_total: number
  clusters_new: number
  needs_review: string[]
  plan_id: string | null
  decisions: Decision[]
  summary: string
}

export type UIActionKind =
  | "focus_cluster"
  | "show_plan"
  | "show_run"
  | "show_crew"
  | "set_filter"
  | "show_trip"
  | "open_report_form"

export type UIAction = { kind: UIActionKind; payload: Record<string, unknown> }

export type PendingAction = {
  id: string
  tool: string
  args: Record<string, unknown>
  summary: string
}

export type UIStateDto = {
  role: "supervisor" | "crew" | "citizen"
  bbox: [number, number, number, number] | null
  selected_cluster_id: string | null
  filters: Record<string, unknown>
}

export type AssistantRequest = {
  session_id: string
  message: string
  ui_state: UIStateDto
}

export type AssistantResponse = {
  text: string
  actions: UIAction[]
  pending: PendingAction | null
  trace: string[]
}

export const CATEGORY_TO_SKILL: Record<string, string> = {
  pothole: "road",
  manhole: "road",
  traffic_sign: "road",
  streetlight: "electric",
  garbage: "sanitation",
  public_space: "sanitation",
  water_leak: "water",
  tree: "green",
}

export const CATEGORY_SERVICE_MIN: Record<string, number> = {
  pothole: 45,
  manhole: 30,
  traffic_sign: 30,
  streetlight: 25,
  garbage: 20,
  public_space: 40,
  water_leak: 90,
  tree: 60,
}

export const SKILLS = [
  "road",
  "electric",
  "sanitation",
  "water",
  "green",
] as const

export const SKILL_LABELS: Record<string, string> = {
  road: "дорожная",
  electric: "электрики",
  sanitation: "санитарная",
  water: "водоканал",
  green: "зелёное хозяйство",
}

/** Кусок fixture demo_city.json, который нужен mock-уровню. */
export type DemoReport = Omit<
  Report,
  "extracted" | "verification" | "cluster_id" | "lang" | "source"
> & {
  lang?: Report["lang"]
  source?: Report["source"]
}

export type DemoCity = {
  now: string
  reports: DemoReport[]
  infrastructure: InfraObject[]
  events: Event[]
  crews: Crew[]
  weather: { clear: Weather; storm: Weather }
  expect: {
    open_reports: number
    clusters: number
    dup_trio: string[]
    jobs_after_batching: number
    site_batch: string[]
    top2_priority_reports: string[]
    min_score_manhole: number
    min_score_school_pothole: number
    low_noise_report: string
    max_score_low_noise: number
    suspicious_report: string
    recurrence_report: string
    storm_defers_categories: string[]
    storm_boosts_categories: string[]
  }
}
