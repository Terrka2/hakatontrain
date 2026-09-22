// Инварианты mock-«города» против fixture.expect. Запуск: node --test src/lib/mock-city.test.ts
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { test } from "node:test"

import type { DemoCity, JobUpdate } from "./contracts.ts"
import { buildPlan, clusterOuts, mockAssistantReply } from "./mock-city.ts"

const demo = JSON.parse(
  readFileSync(join(import.meta.dirname, "../mocks/demo_city.json"), "utf8"),
) as DemoCity
const e = demo.expect

test("кластеры: expect.clusters, топ-2 у детсада и лицея, баллы по expect", () => {
  const { items } = clusterOuts(demo, null)
  assert.equal(items.length, e.clusters)
  assert.deepEqual(
    new Set(items.slice(0, 2).map((c) => c.report_ids[0])),
    new Set(e.top2_priority_reports),
  )
  const by = (id: string) => items.find((c) => c.report_ids.includes(id))!
  assert.ok(by("r011").score >= e.min_score_manhole)
  assert.ok(by("r011").priority.factors.some((f) => f.code === "FL"))
  assert.ok(by("r001").score >= e.min_score_school_pothole)
  assert.ok(by(e.low_noise_report).score <= e.max_score_low_noise)
  assert.equal(by(e.suspicious_report).needs_review, true)
  const rc = by(e.recurrence_report).priority.factors.find(
    (f) => f.code === "RC",
  )!
  assert.equal(rc.score, 1)
  assert.ok(rc.evidence.join(" ").includes("r016"))
})

test("сумма points факторов = балл; EX без данных", () => {
  for (const c of clusterOuts(demo, null).items) {
    const sum = c.priority.factors.reduce((s, f) => s + f.points, 0)
    assert.ok(Math.abs(sum - c.score) <= 0.3, `${c.id}: ${sum} vs ${c.score}`)
    assert.equal(c.priority.factors.find((f) => f.code === "EX")!.score, null)
    for (const f of c.priority.factors)
      if (f.score && f.score > 0)
        assert.ok(f.evidence.length, `${c.id} ${f.code} без evidence`)
  }
})

test("план: expect.jobs_after_batching выездов, site_batch одним выездом, три маршрута", () => {
  const { items } = clusterOuts(demo, demo.weather.clear)
  const plan = buildPlan(items, demo, "clear", 1)
  assert.equal(plan.jobs.length, e.jobs_after_batching)
  const site = plan.jobs.find((j) => j.cluster_ids.length > 1)!
  assert.deepEqual(
    new Set(site.cluster_ids),
    new Set(e.site_batch.map((id) => `cl-${id}`)),
  )
  assert.equal(plan.routes.length, demo.crews.length)
  assert.ok(
    plan.routes.every((r) => r.stops.length > 0),
    "у каждой бригады есть выезды",
  )
  assert.equal(plan.unassigned.length, 0)
  assert.ok(plan.total_priority >= plan.baseline_total_priority)
  for (const r of plan.routes)
    for (let i = 1; i < r.stops.length; i++)
      assert.ok(r.stops[i].arrival >= r.stops[i - 1].departure)
})

test("шторм: ямы отложены, деревья подняты", () => {
  const { items } = clusterOuts(demo, demo.weather.storm)
  const plan = buildPlan(items, demo, "storm", 2)
  const cats = plan.jobs.map(
    (j) => items.find((c) => c.id === j.cluster_ids[0])!.category,
  )
  for (const cat of e.storm_defers_categories)
    assert.ok(!cats.includes(cat), `${cat} не отложена`)
  assert.ok(plan.decisions.some((d) => d.kind === "defer"))
  assert.ok(plan.decisions.some((d) => d.kind === "boost"))
})

test("переопределение навыка переносит задание другой бригаде", () => {
  const { items } = clusterOuts(demo, null)
  const p1 = buildPlan(items, demo, "clear", 1)
  const job = p1.routes.find((r) => r.crew_id === "c1")!.stops[0].job_id
  const p2 = buildPlan(items, demo, "clear", 2, [], [], { [job]: "electric" })
  assert.ok(
    p2.routes
      .find((r) => r.crew_id === "c2")!
      .stops.some((s) => s.job_id === job),
  )
})

test("ассистент: интенты и pending только у «утверди»", () => {
  const { items } = clusterOuts(demo, null)
  const draft = buildPlan(items, demo, "clear", 1)
  const ui = {
    role: "supervisor" as const,
    bbox: null,
    selected_cluster_id: null,
    filters: {},
  }
  const ctx = { items, runs: [], draft, weather: "clear" as const }
  assert.equal(
    mockAssistantReply(
      { session_id: "s", message: "Утверди план", ui_state: ui },
      ctx,
    ).pending?.tool,
    "approve_plan",
  )
  assert.equal(
    mockAssistantReply(
      { session_id: "s", message: "Почему это первое?", ui_state: ui },
      ctx,
    ).actions[0].kind,
    "focus_cluster",
  )
  assert.equal(
    mockAssistantReply(
      { session_id: "s", message: "Пошёл ливень", ui_state: ui },
      ctx,
    ).pending,
    null,
  )
  const upd: JobUpdate = {
    job_id: "x",
    crew_id: "c1",
    status: "failed",
    at: demo.now,
    photo_url: null,
    reason: "other",
    needs_skill: null,
    note: null,
  }
  assert.equal(upd.status, "failed")
})
