import { CheckCircle2, CloudRain, RotateCcw, Sun } from "lucide-react"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { CityMap, useClusters } from "@/features/map"
import useAuth from "@/hooks/useAuth"
import { USE_MOCK } from "@/lib/api"
import { useMockCity } from "@/lib/mock-store"
import { cn } from "@/lib/utils"
import { ApproveBar } from "./ApproveBar"
import { DecisionLog } from "./DecisionLog"
import { OperatorFeed } from "./OperatorFeed"
import { PlanDiff } from "./PlanDiff"
import { PlanView } from "./PlanView"
import { PlanVsBaseline } from "./PlanVsBaseline"
import {
  useApproved,
  useCrews,
  useDispatchActions,
  useDraft,
  useRuns,
} from "./useDispatch"

function Section({
  title,
  children,
  className,
}: {
  title: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <section className={cn("rounded-xl border bg-card p-4", className)}>
      <h2 className="mb-3 text-sm font-semibold">{title}</h2>
      {children}
    </section>
  )
}

/** Пульт руководителя: карта с маршрутами, лента оператора, план, что изменилось, одна кнопка «Утвердить». */
export function DispatchScreen() {
  const runs = useRuns()
  const draft = useDraft()
  const approved = useApproved()
  const crews = useCrews()
  const clusters = useClusters()
  const { approveMut, weatherMut, resetMut } = useDispatchActions()
  const { user } = useAuth()
  const { weather } = useMockCity()

  // Без бэкенда (mock) роли нет — считаем руководителем. С бэкендом решает роль пользователя.
  const role = user?.role
  const isSupervisor = role
    ? role === "supervisor" || Boolean(user?.is_superuser)
    : USE_MOCK
  const draftPlan = draft.data ?? null
  const approvedPlan = approved.data ?? null
  const shown = draftPlan ?? approvedPlan
  const loading =
    runs.isPending || draft.isPending || approved.isPending || crews.isPending
  const failed =
    runs.error ?? draft.error ?? approved.error ?? crews.error ?? clusters.error

  const retryAll = () => {
    runs.refetch()
    draft.refetch()
    approved.refetch()
    crews.refetch()
  }

  const demoButtons = (
    <div className="flex flex-wrap items-center gap-2">
      <fieldset
        className="m-0 flex min-w-0 rounded-md border p-0"
        aria-label="Погода"
      >
        <Button
          variant={weather === "clear" ? "secondary" : "ghost"}
          size="sm"
          className="min-h-10 rounded-r-none"
          onClick={() => weatherMut.mutate("clear")}
          disabled={weatherMut.isPending}
          aria-pressed={weather === "clear"}
        >
          <Sun aria-hidden /> Ясно
        </Button>
        <Button
          variant={weather === "storm" ? "secondary" : "ghost"}
          size="sm"
          className="min-h-10 rounded-l-none"
          onClick={() => weatherMut.mutate("storm")}
          disabled={weatherMut.isPending}
          aria-pressed={weather === "storm"}
        >
          <CloudRain aria-hidden /> Шторм
        </Button>
      </fieldset>
      <Button
        variant="outline"
        size="sm"
        className="min-h-10"
        onClick={() => resetMut.mutate()}
        disabled={resetMut.isPending}
      >
        <RotateCcw aria-hidden /> Сброс демо
      </Button>
    </div>
  )

  return (
    <div className="flex flex-col gap-4" data-testid="dispatch-screen">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">План и бригады</h1>
        {demoButtons}
      </div>

      {failed ? (
        <ErrorState
          title="Пульт без данных"
          error={failed}
          onRetry={retryAll}
        />
      ) : loading ? (
        <Skeleton rows={4} />
      ) : (
        <>
          {draftPlan ? (
            <ApproveBar
              draft={draftPlan}
              onApprove={() => approveMut.mutate(draftPlan.id)}
              canApprove={isSupervisor}
              busy={approveMut.isPending}
            />
          ) : approvedPlan ? (
            <div
              className="flex items-center gap-3 rounded-xl border bg-card p-3"
              data-testid="plan-approved"
            >
              <CheckCircle2
                className="size-5 shrink-0 text-status-resolved"
                aria-hidden
              />
              <div>
                <p className="text-sm font-semibold">
                  План v{approvedPlan.version} отправлен бригадам
                </p>
                <p className="text-xs text-muted-foreground">
                  Утвердил {approvedPlan.approved_by ?? "руководитель"} ·
                  бригады видят свои маршруты
                </p>
              </div>
            </div>
          ) : null}

          <div className="h-[40vh] min-h-64 overflow-hidden rounded-xl border md:h-[52vh]">
            <CityMap
              className="h-full"
              layers={[
                ...(clusters.data
                  ? [{ kind: "clusters" as const, items: clusters.data }]
                  : []),
                ...(shown
                  ? [{ kind: "routes" as const, routes: shown.routes }]
                  : []),
              ]}
            />
          </div>

          {!shown ? (
            <EmptyState
              title="Оператор ещё не собирал план"
              hint="Нажмите «Сброс демо» — оператор импортирует обращения и соберёт черновик."
            />
          ) : (
            <>
              <Section
                title={`Маршруты · план v${shown.version}${shown.status === "approved" ? " · отправлен бригадам" : " · черновик"}`}
              >
                <PlanView
                  plan={shown}
                  crews={crews.data ?? []}
                  clusters={clusters.data ?? []}
                />
              </Section>
              <div className="grid gap-4 lg:grid-cols-2">
                <Section title="Лента оператора">
                  <OperatorFeed runs={runs.data ?? []} />
                </Section>
                <Section title="Что изменилось">
                  {draftPlan ? (
                    <PlanDiff current={approvedPlan} draft={draftPlan} />
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Черновика нет: действует утверждённый план.
                    </p>
                  )}
                  <div className="mt-4 border-t pt-3">
                    <PlanVsBaseline
                      total={shown.total_priority}
                      baseline={shown.baseline_total_priority}
                    />
                  </div>
                </Section>
              </div>
              <Section title="Журнал решений">
                <DecisionLog decisions={shown.decisions} />
              </Section>
            </>
          )}
        </>
      )}
    </div>
  )
}
