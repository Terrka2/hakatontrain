// Тесты F5 на критерии приёмки 3 и 5 и на вспомогательную логику. Запуск: node --test src/features/crew/logic.test.ts
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { test } from "node:test"

import type { DemoCity } from "../../lib/contracts.ts"
import { buildPlan, clusterOuts } from "../../lib/mock-city.ts"
import {
  buildUpdate,
  canFinish,
  geoLink,
  nextStop,
  routeChanged,
} from "./logic.ts"

const demo = JSON.parse(
  readFileSync(join(import.meta.dirname, "../../mocks/demo_city.json"), "utf8"),
) as DemoCity

function c1Route() {
  const { items } = clusterOuts(demo, null)
  const plan = buildPlan(items, demo, "clear", 1)
  return plan.routes.find((r) => r.crew_id === "c1")!
}

test("mock: у бригады c1 есть остановки, nextStop — первая незакрытая", () => {
  const route = c1Route()
  assert.ok(route.stops.length >= 2)
  assert.equal(nextStop(route)?.job_id, route.stops[0].job_id)
  const closed = {
    ...route,
    stops: route.stops.map((s, i) =>
      i === 0 ? { ...s, status: "done" as const } : s,
    ),
  }
  assert.equal(nextStop(closed)?.job_id, route.stops[1].job_id)
  const arrived = {
    ...route,
    stops: route.stops.map((s, i) =>
      i === 0 ? { ...s, status: "arrived" as const } : s,
    ),
  }
  assert.equal(nextStop(arrived)?.job_id, route.stops[0].job_id)
  assert.equal(nextStop({ ...route, stops: [] }), null)
  assert.equal(nextStop(null), null)
})

test("критерий 3: «Сделано» без фото недоступно, «Не могу» требует причину и навык", () => {
  assert.equal(canFinish(false), false)
  assert.equal(canFinish(true), true)
  const base = { jobId: "j", crewId: "c1", at: demo.now }
  assert.throws(() => buildUpdate({ ...base, status: "done" }), /фото/)
  assert.equal(
    buildUpdate({ ...base, status: "done", photoUrl: "blob:x" }).photo_url,
    "blob:x",
  )
  assert.throws(() => buildUpdate({ ...base, status: "failed" }), /причину/)
  assert.throws(
    () =>
      buildUpdate({ ...base, status: "failed", reason: "needs_other_skill" }),
    /бригада/,
  )
  const u = buildUpdate({
    ...base,
    status: "failed",
    reason: "needs_other_skill",
    needsSkill: "electric",
    note: "  провод  ",
  })
  assert.equal(u.needs_skill, "electric")
  assert.equal(u.note, "провод")
  assert.equal(u.photo_url, null)
  const a = buildUpdate({
    ...base,
    status: "arrived",
    reason: "other",
    photoUrl: "x",
  })
  assert.equal(a.reason, null)
  assert.equal(a.photo_url, null)
})

test("критерий 5: баннер только при смене версии утверждённого плана", () => {
  assert.equal(routeChanged(undefined, 1), false)
  assert.equal(routeChanged(null, 1), false)
  assert.equal(routeChanged(1, 1), false)
  assert.equal(routeChanged(1, 2), true)
})

test("geo-ссылка для навигатора", () => {
  assert.equal(geoLink({ lat: 47.018, lon: 28.842 }), "geo:47.018,28.842")
})
