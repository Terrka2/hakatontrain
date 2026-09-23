// Чистая логика экрана бригады: без React и алиасов, тестируется node --test.
import type {
  CrewRoute,
  FailReason,
  GeoPoint,
  JobUpdate,
  RouteStop,
} from "../../lib/contracts.ts"

/** Следующая остановка: первая, которую ещё не закрыли («сделано» или «не могу»). */
export function nextStop(
  route: CrewRoute | null | undefined,
): RouteStop | null {
  if (!route) return null
  return (
    route.stops.find((s) => s.status === "pending" || s.status === "arrived") ??
    null
  )
}

/** «Сделано» доступно только с фото. */
export function canFinish(hasPhoto: boolean): boolean {
  return hasPhoto
}

export type UpdateInput = {
  jobId: string
  crewId: string
  status: JobUpdate["status"]
  at: string
  photoUrl?: string | null
  reason?: FailReason | null
  needsSkill?: string | null
  note?: string | null
}

/** Собирает JobUpdate по правилам контракта. Бросает Error с понятной причиной, если данных не хватает. */
export function buildUpdate(input: UpdateInput): JobUpdate {
  if (input.status === "done" && !input.photoUrl)
    throw new Error("«Сделано» требует фото")
  if (input.status === "failed" && !input.reason)
    throw new Error("«Не могу» требует причину")
  if (
    input.status === "failed" &&
    input.reason === "needs_other_skill" &&
    !input.needsSkill
  )
    throw new Error("Укажите, какая бригада нужна")
  const failed = input.status === "failed"
  return {
    job_id: input.jobId,
    crew_id: input.crewId,
    status: input.status,
    at: input.at,
    photo_url: input.status === "done" ? (input.photoUrl ?? null) : null,
    reason: failed ? (input.reason ?? null) : null,
    needs_skill:
      failed && input.reason === "needs_other_skill"
        ? (input.needsSkill ?? null)
        : null,
    note: failed ? input.note?.trim() || null : null,
  }
}

/** Баннер «Маршрут обновлён»: только когда уже видели одну версию и пришла другая. */
export function routeChanged(
  prevVersion: number | null | undefined,
  nextVersion: number | null | undefined,
): boolean {
  return (
    prevVersion != null && nextVersion != null && prevVersion !== nextVersion
  )
}

/** Ссылка для навигатора телефона. */
export function geoLink(p: GeoPoint): string {
  return `geo:${p.lat},${p.lon}`
}

export const FAIL_REASONS: { value: FailReason; label: string }[] = [
  { value: "no_access", label: "Нет доступа к месту" },
  { value: "needs_other_skill", label: "Нужна другая бригада" },
  { value: "not_found", label: "Проблему не нашли" },
  { value: "weather", label: "Погода не позволяет" },
  { value: "other", label: "Другое" },
]

export function formatTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return "—"
  return d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
}
