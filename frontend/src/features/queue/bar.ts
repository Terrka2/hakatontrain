// Чистая логика PriorityBar: сегменты полосы по факторам. Тестируется node --test без браузера.
import type { Factor } from "@/lib/contracts"

export type Segment = {
  code: string
  label: string
  /** Подпись «+23». */
  points: number
  /** Ширина сегмента в процентах от полосы. */
  width: number
  evidence: string
  /** Фактор без данных: серый, ширины нет. */
  noData: boolean
}

/** Сегменты в порядке убывания вклада; факторы без данных — в конце. Сумма points = score. */
export function segments(factors: Factor[], score: number): Segment[] {
  const total = score > 0 ? score : 1
  const withData = factors
    .filter((f) => f.score !== null)
    .map(
      (f): Segment => ({
        code: f.code,
        label: f.label,
        points: Math.round(f.points * 10) / 10,
        width: Math.max(0, Math.round((f.points / total) * 1000) / 10),
        evidence: f.evidence[0] ?? "",
        noData: false,
      }),
    )
    .sort((a, b) => b.points - a.points)
  // Сервер округляет каждый фактор до 0.1 — остаток округления показываем на самом крупном сегменте,
  // чтобы подписи сходились с баллом копейка в копейку.
  if (withData.length > 0) {
    const residual =
      Math.round((score - withData.reduce((s, x) => s + x.points, 0)) * 10) / 10
    if (Math.abs(residual) <= 0.5)
      withData[0].points = Math.round((withData[0].points + residual) * 10) / 10
    // Ширины — от итоговых подписей; полоса не длиннее 100 %.
    let used = 0
    for (const s of withData) {
      s.width = Math.max(
        0,
        Math.min(100 - used, Math.round((s.points / total) * 1000) / 10),
      )
      used += s.width
    }
  }
  const noData = factors
    .filter((f) => f.score === null)
    .map(
      (f): Segment => ({
        code: f.code,
        label: f.label,
        points: 0,
        width: 0,
        evidence: "",
        noData: true,
      }),
    )
  return [...withData, ...noData]
}

/** Сумма подписей сегментов — для проверки критерия 2. */
export function segmentsTotal(segs: Segment[]): number {
  return Math.round(segs.reduce((s, x) => s + x.points, 0) * 10) / 10
}

/** Tailwind-класс цвета сегмента по коду фактора — только токены темы. */
export function segmentColor(code: string): string {
  const map: Record<string, string> = {
    HZ: "bg-priority-high",
    DM: "bg-chart-2",
    AG: "bg-chart-3",
    SP: "bg-chart-4",
    RC: "bg-chart-5",
    WX: "bg-chart-1",
    VF: "bg-primary",
    EX: "bg-muted-foreground",
    FL: "bg-priority-high/50",
  }
  return map[code] ?? "bg-muted-foreground"
}
