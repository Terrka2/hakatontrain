// Тесты F2. Запуск: node --test src/features/queue/bar.test.ts (без сети, без браузера).
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { test } from "node:test"

import type { DemoCity } from "../../lib/contracts.ts"
import { clusterOuts } from "../../lib/mock-city.ts"
import { segmentColor, segments, segmentsTotal } from "./bar.ts"

const demo = JSON.parse(
  readFileSync(join(import.meta.dirname, "../../mocks/demo_city.json"), "utf8"),
) as DemoCity
const { items, reports } = clusterOuts(demo, null)

test("критерий 2: сумма подписей сегментов PriorityBar = балл (все кластеры mock)", () => {
  for (const c of items) {
    const segs = segments(c.priority.factors, c.score)
    assert.ok(
      Math.abs(segmentsTotal(segs) - c.score) <= 0.1,
      `${c.id}: ${segmentsTotal(segs)} vs ${c.score}`,
    )
    const width = segs.reduce((s, x) => s + x.width, 0)
    assert.ok(width <= 100.5, `${c.id}: ширина ${width}%`)
  }
})

test("факторы без данных — серые, без ширины, в конце списка", () => {
  const c = items[0]
  const segs = segments(c.priority.factors, c.score)
  const ex = segs.find((s) => s.code === "EX")
  assert.ok(ex?.noData)
  assert.equal(ex.width, 0)
  assert.equal(
    segs.findIndex((s) => s.noData),
    segs.filter((s) => !s.noData).length,
  )
  const withData = segs.filter((s) => !s.noData)
  for (let i = 1; i < withData.length; i++)
    assert.ok(withData[i - 1].points >= withData[i].points)
})

test("границы: score=0 и пустой список факторов", () => {
  assert.deepEqual(segments([], 0), [])
  const one = segments(
    [
      {
        code: "HZ",
        label: "Опасность",
        score: 0,
        weight: 0.25,
        points: 0,
        evidence: [],
      },
    ],
    0,
  )
  assert.equal(one[0].width, 0)
  assert.equal(segmentsTotal(one), 0)
})

test("критерий 3: r006 в очереди с needs_review и причинами", () => {
  const c = items.find((x) =>
    x.report_ids.includes(demo.expect.suspicious_report),
  )
  assert.ok(c?.needs_review)
  const reasons = c.report_ids.flatMap(
    (id) => reports.find((r) => r.id === id)?.verification?.reasons ?? [],
  )
  assert.ok(reasons.length > 0)
})

test("цвета сегментов — только классы токенов", () => {
  for (const code of [
    "HZ",
    "DM",
    "AG",
    "SP",
    "RC",
    "WX",
    "VF",
    "EX",
    "FL",
    "??",
  ])
    assert.match(segmentColor(code), /^bg-[a-z0-9/-]+$/)
})
