// Тесты F1. Критерии по данным (13 маркеров, топ-2) живут в lib/mock-city.test.ts; здесь — геометрия карты.
import assert from "node:assert/strict"
import { test } from "node:test"

import { markerSize } from "./clusters.ts"
import { routeColorVar, routeFeatures } from "./routes.ts"

test("размер маркера растёт с числом обращений и ограничен", () => {
  assert.equal(markerSize(1), 28)
  assert.equal(markerSize(3), 40)
  assert.equal(markerSize(50), 52)
})

test("слой маршрутов: линия на бригаду, цвет из токена по индексу, пройденное отдельно", () => {
  const route = {
    crew_id: "c2",
    geometry: [
      { lat: 47, lon: 28 },
      { lat: 47.01, lon: 28.01 },
      { lat: 47.02, lon: 28.02 },
    ],
    stops: [
      {
        job_id: "a",
        location: { lat: 47.01, lon: 28.01 },
        arrival: "",
        departure: "",
        status: "done" as const,
      },
      {
        job_id: "b",
        location: { lat: 47.02, lon: 28.02 },
        arrival: "",
        departure: "",
        status: "pending" as const,
      },
    ],
    drive_min: 0,
    work_min: 0,
  }
  const f = routeFeatures([route], ["c1", "c2", "c3"])
  assert.equal(f.features.length, 2)
  assert.deepEqual(
    f.features.map((x) => x.properties.part),
    ["done", "ahead"],
  )
  assert.equal(f.features[0].properties.crew, "c2")
  assert.equal(routeColorVar(1), "--crew-2")
  assert.deepEqual(routeFeatures([], []).features, [])
})
