// Тесты F4 на критерий приёмки 2. Запуск: node --test src/features/assistant/actions.test.ts
import assert from "node:assert/strict"
import { test } from "node:test"

import { type ActionDeps, runUiActions } from "./actions.ts"

function fakeDeps() {
  const log: string[] = []
  let filters: Record<string, unknown> = { weather: "clear" }
  const deps: ActionDeps = {
    navigate: (to) => log.push(`nav:${to}`),
    setUiState: (patch) => {
      if (patch.filters) filters = patch.filters
      log.push(`state:${JSON.stringify(patch)}`)
    },
    getFilters: () => filters,
  }
  return { deps, log, filters: () => filters }
}

test("критерий 2: show_plan открывает экран плана", () => {
  const { deps, log } = fakeDeps()
  assert.deepEqual(runUiActions([{ kind: "show_plan", payload: {} }], deps), [
    "plan",
  ])
  assert.deepEqual(log, ["nav:/plan"])
})

test("критерий 2: focus_cluster выбирает кластер и ведёт на карту", () => {
  const { deps, log } = fakeDeps()
  runUiActions(
    [{ kind: "focus_cluster", payload: { cluster_id: "cl-r001" } }],
    deps,
  )
  assert.deepEqual(log, ['state:{"selected_cluster_id":"cl-r001"}', "nav:/"])
})

test("set_filter дополняет фильтры, show_run кладёт run_id, неизвестные действия игнорируются", () => {
  const { deps, log, filters } = fakeDeps()
  const done = runUiActions(
    [
      { kind: "set_filter", payload: { weather: "storm" } },
      { kind: "show_run", payload: { run_id: "run-2" } },
      { kind: "show_crew", payload: {} },
      { kind: "show_trip", payload: {} },
      { kind: "focus_cluster", payload: {} },
    ],
    deps,
  )
  assert.deepEqual(done, ["filter:weather", "run:run-2", "crew"])
  assert.deepEqual(filters(), { weather: "storm", run_id: "run-2" })
  assert.ok(log.includes("nav:/plan") && log.includes("nav:/crew"))
})

test("пустой список действий ничего не делает", () => {
  const { deps, log } = fakeDeps()
  assert.deepEqual(runUiActions([], deps), [])
  assert.deepEqual(log, [])
})
