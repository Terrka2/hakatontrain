import { AlertTriangle, Camera, ThumbsUp } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { CategoryIcon } from "@/components/ui/CategoryIcon"
import { PriorityBadge } from "@/components/ui/PriorityBadge"
import { StatusBadge } from "@/components/ui/StatusBadge"
import type { ClusterOut, Report } from "@/lib/contracts"
import { categoryInfo } from "@/theme/categories"
import { type ReviewDecision, reviewCluster } from "./api"
import { PriorityBar } from "./PriorityBar"

type Props = { cluster: ClusterOut; reports: Report[]; canReview?: boolean }

const LANG: Record<string, string> = { ru: "рус", ro: "rom", en: "eng" }

function short(iso: string): string {
  const d = new Date(iso)
  return `${d.getDate().toString().padStart(2, "0")}.${(d.getMonth() + 1).toString().padStart(2, "0")}`
}

/** Карточка проблемы: почему такой балл, из каких обращений склеена, что решить руководителю. */
export function ClusterCard({ cluster, reports, canReview = true }: Props) {
  const [decision, setDecision] = useState<ReviewDecision | null>(null)
  const own = cluster.report_ids
    .map((id) => reports.find((r) => r.id === id))
    .filter((r): r is Report => Boolean(r))
  const reasons = own.flatMap((r) => r.verification?.reasons ?? [])
  const needsReview = cluster.needs_review && decision === null

  const decide = async (d: ReviewDecision) => {
    setDecision(d)
    await reviewCluster(cluster.id, d)
  }

  return (
    <article
      className="flex flex-col gap-4"
      aria-label="Карточка проблемы"
      data-testid="cluster-card"
    >
      <div className="flex items-start gap-3">
        <CategoryIcon
          category={cluster.category}
          className="mt-0.5 size-6 shrink-0 text-muted-foreground"
        />
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold leading-tight">
            {categoryInfo(cluster.category).label}
          </h2>
          <p className="truncate text-sm text-muted-foreground">
            {cluster.address ?? "Адрес не указан"}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <PriorityBadge score={cluster.score} needsReview={needsReview} />
        <StatusBadge status={cluster.status} />
        <span className="text-xs text-muted-foreground">
          с {short(cluster.first_reported_at)}
        </span>
      </div>

      {needsReview && (
        <div
          className="flex flex-col gap-2 rounded-lg border border-priority-mid/60 bg-priority-mid/10 p-3"
          role="note"
        >
          <p className="flex items-center gap-2 text-sm font-medium">
            <AlertTriangle className="size-4 text-priority-mid" aria-hidden />
            Требует проверки
          </p>
          {reasons.length > 0 && (
            <ul className="list-disc pl-5 text-sm text-muted-foreground">
              {reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
          {canReview && (
            <div className="flex gap-2 pt-1">
              <Button
                size="lg"
                className="min-h-12 flex-1"
                onClick={() => decide("accept")}
              >
                Принять
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="min-h-12 flex-1"
                onClick={() => decide("reject")}
              >
                Отклонить
              </Button>
            </div>
          )}
        </div>
      )}
      {decision && (
        <p className="text-sm text-muted-foreground">
          {decision === "accept"
            ? "Принято: проблема пойдёт в план."
            : "Отклонено: обращение закрыто как недостоверное."}
        </p>
      )}

      <PriorityBar factors={cluster.priority.factors} score={cluster.score} />

      <section className="flex flex-col gap-2" aria-label="Обращения">
        <h3 className="text-sm text-muted-foreground">
          {own.length === 1 ? "Обращение" : `Обращения: ${own.length}`}
        </h3>
        <ul className="flex flex-col gap-3">
          {own.map((r) => (
            <li
              key={r.id}
              className="flex flex-col gap-1 rounded-lg border p-3"
            >
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span className="font-mono">{r.id}</span>
                <span>{short(r.created_at)}</span>
                {r.lang && (
                  <span className="rounded bg-muted px-1.5 py-0.5">
                    {LANG[r.lang] ?? r.lang}
                  </span>
                )}
                {r.photo_url && (
                  <Camera className="size-3.5" aria-label="Есть фото" />
                )}
                {r.confirmations > 0 && (
                  <span
                    className="flex items-center gap-1"
                    title="Подтверждения жителей"
                  >
                    <ThumbsUp className="size-3.5" aria-hidden />
                    {r.confirmations}
                  </span>
                )}
              </div>
              <p className="text-sm leading-relaxed">{r.text}</p>
            </li>
          ))}
        </ul>
        {cluster.links.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Почему склеено:{" "}
            {cluster.links
              .map(
                (l) =>
                  `${l.a} и ${l.b} — ${l.distance_m} м, сходство ${l.text_sim.toFixed(2)}`,
              )
              .join("; ")}
          </p>
        )}
      </section>
    </article>
  )
}
