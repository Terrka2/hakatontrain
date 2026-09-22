// Тесты F1 на критерии приёмки. Запуск: node --test src/features/map/clusters.test.ts (без сети).
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { test } from "node:test"

import { clustersFromDemo, distanceM, markerSize } from "./clusters.ts"
import type { DemoCity } from "./types.ts"

const demo = JSON.parse(
  readFileSync(join(import.meta.dirname, "../../mocks/demo_city.json"), "utf8"),
) as DemoCity & {
  expect: {
    clusters: number
    top2_priority_reports: string[]
    low_noise_report: string
    max_score_low_noise: number
    min_score_manhole: number
    min_score_school_pothole: number
  }
}

test("критерий 1: из mock выходит expect.clusters маркеров", () => {
  const clusters = clustersFromDemo(demo)
  assert.equal(clusters.length, demo.expect.clusters)
  assert.equal(new Set(clusters.map((c) => c.id)).size, clusters.length)
})

test("критерий 1: самые красные — у лицея (r001) и у детсада (r011)", () => {
  const [first, second] = clustersFromDemo(demo)
  const top = new Set([first.report_ids[0], second.report_ids[0]])
  assert.deepEqual(top, new Set(demo.expect.top2_priority_reports))
  assert.ok(first.score >= 70 && second.score >= 70)
})

test("баллы согласованы с expect: люк ≥ 80, яма у школы ≥ 70, шум ≤ 30, r006 — на проверку", () => {
  const byReport = (id: string) =>
    clustersFromDemo(demo).find((c) => c.report_ids.includes(id))!
  assert.ok(byReport("r011").score >= demo.expect.min_score_manhole)
  assert.ok(byReport("r001").score >= demo.expect.min_score_school_pothole)
  assert.ok(
    byReport(demo.expect.low_noise_report).score <=
      demo.expect.max_score_low_noise,
  )
  assert.equal(byReport(demo.expect.suspicious_report).needs_review, true)
  assert.equal(byReport("r001").report_ids.length, 3)
})

test("границы: пусто, один элемент, дубликаты id, пробелы в категории", () => {
  const empty: DemoCity = {
    reports: [],
    infrastructure: [],
    expect: { dup_trio: [], suspicious_report: "" },
  }
  assert.deepEqual(clustersFromDemo(empty), [])
  const one = {
    ...empty,
    reports: [{ ...demo.reports[4], category: " Public_Space " }],
  }
  assert.equal(clustersFromDemo(one).length, 1)
  assert.equal(clustersFromDemo(one)[0].score, 20)
  const dup = { ...empty, reports: [demo.reports[0], demo.reports[0]] }
  assert.equal(clustersFromDemo(dup).length, 1)
})

test("детерминированность: два вызова — одинаковый порядок", () => {
  assert.deepEqual(clustersFromDemo(demo), clustersFromDemo(demo))
})

test("размер маркера растёт с числом обращений и ограничен", () => {
  assert.equal(markerSize(1), 28)
  assert.equal(markerSize(3), 40)
  assert.equal(markerSize(50), 52)
  assert.ok(distanceM({ lat: 47, lon: 28 }, { lat: 47.001, lon: 28 }) > 100)
})
