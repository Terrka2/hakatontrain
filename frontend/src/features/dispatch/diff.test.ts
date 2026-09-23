// Тесты F3: сравнение планов и подписи. Запуск: node --test src/features/dispatch/diff.test.ts
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { test } from "node:test"

import type { DemoCity, OperatorRun } from "../../lib/contracts.ts"
import { buildPlan, clusterOuts } from "../../lib/mock-city.ts"
import { feedLine, gainPercent, planDiff, stopLabel } from "./diff.ts"

const demo = JSON.parse(
  readFileSync(join(import.meta.dirname, "../../mocks/demo_city.json"), "utf8"),
) as DemoCity
const { items } = clusterOuts(demo, demo.weather.clear)

test("planDiff: первый черновик — всё добавлено; тот же план — пусто", () => {
  const v1 = buildPlan(items, demo, "clear", 1)
  const first = planDiff(null, v1)
  assert.equal(first.added.length, demo.expect.jobs_after_batching)
  assert.deepEqual(planDiff(v1, v1), { added: [], removed: [], moved: [] })
})

test("planDiff: задание с новым навыком переезжает к другой бригаде", () => {
  const v1 = buildPlan(items, demo, "clear", 1)
  const job = v1.routes.find((r) => r.crew_id === "c1")!.stops[0].job_id
  const v2 = buildPlan(items, demo, "clear", 2, [], [], { [job]: "electric" })
  const d = planDiff(v1, v2)
  assert.deepEqual(
    d.moved.map((m) => m.job_id),
    [job],
  )
  assert.equal(d.moved[0].from, "c1")
  assert.equal(d.moved[0].to, "c2")
  assert.deepEqual(d.added, [])
})

test("planDiff: шторм убирает ямы из плана", () => {
  const v1 = buildPlan(items, demo, "clear", 1)
  const v2 = buildPlan(
    clusterOuts(demo, demo.weather.storm).items,
    demo,
    "storm",
    2,
  )
  const d = planDiff(v1, v2)
  assert.ok(d.removed.length > 0)
  assert.ok(
    d.removed.some((id) => id.endsWith("-site")),
    "объединённый выезд по ямам отложен",
  )
})

test("stopLabel: «4 проблемы · 1 выезд» для объединённой остановки", () => {
  const v1 = buildPlan(items, demo, "clear", 1)
  const site = v1.jobs.find((j) => j.cluster_ids.length > 1)!
  assert.equal(stopLabel(site), "4 проблемы · 1 выезд")
  assert.equal(
    stopLabel(v1.jobs.find((j) => j.cluster_ids.length === 1)!),
    "1 проблема",
  )
})

test("feedLine: время, триггер по-русски, план vN", () => {
  const run: OperatorRun = {
    id: "run-1",
    trigger: "import",
    at: "2026-09-26T07:02:00+03:00",
    reports_seen: 16,
    clusters_total: 13,
    clusters_new: 13,
    needs_review: ["cl-r006"],
    plan_id: "plan-1",
    decisions: [],
    summary: "",
  }
  assert.equal(
    feedLine(run),
    "07:02 · импорт · 16 обращений → 13 проблем, 1 на проверку, план v1",
  )
  assert.equal(gainPercent(120, 100), 20)
  assert.equal(gainPercent(1, 0), null)
})
