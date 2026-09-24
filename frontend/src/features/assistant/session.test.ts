// Тесты F4 на критерии приёмки 1, 3, 4. Запуск: node --test src/features/assistant/session.test.ts
import assert from "node:assert/strict"
import { test } from "node:test"

import {
  buildRequest,
  ERROR_TEXT,
  initialSession,
  reduceSession,
} from "./session.ts"

const ui = {
  role: "supervisor" as const,
  bbox: [28.8, 47.0, 28.9, 47.05] as [number, number, number, number],
  selected_cluster_id: "cl-r011",
  filters: { weather: "clear" },
}

test("критерий 1: запрос уходит с selected_cluster_id и bbox", () => {
  const req = buildRequest("s1", "  Почему это первое?  ", ui)
  assert.equal(req.session_id, "s1")
  assert.equal(req.message, "Почему это первое?")
  assert.equal(req.ui_state.selected_cluster_id, "cl-r011")
  assert.deepEqual(req.ui_state.bbox, ui.bbox)
  assert.deepEqual(req.ui_state.filters, { weather: "clear" })
  assert.notEqual(req.ui_state.filters, ui.filters, "фильтры копируются")
})

test("критерий 3: pending переводит сессию в ожидание, confirm — только после approve", () => {
  const pending = {
    id: "pending-plan-1",
    tool: "approve_plan",
    args: { plan_id: "plan-1" },
    summary: "Утвердить план v1",
  }
  let s = reduceSession(initialSession, { type: "send", text: "Утверди план" })
  assert.equal(s.busy, true)
  s = reduceSession(s, {
    type: "reply",
    response: { text: "Подтвердите", actions: [], pending, trace: ["guard"] },
  })
  assert.equal(s.busy, false)
  assert.deepEqual(s.pending, pending)
  const declined = reduceSession(s, { type: "decide", approve: false })
  assert.equal(declined.pending, null)
  assert.equal(declined.busy, false, "без подтверждения запрос не уходит")
  const approved = reduceSession(s, { type: "decide", approve: true })
  assert.equal(approved.pending, null)
  assert.equal(approved.busy, true, "подтверждение — запрос confirm в пути")
})

test("критерий 4: ошибка попадает в историю, история не теряется", () => {
  let s = reduceSession(initialSession, { type: "send", text: "Привет" })
  s = reduceSession(s, {
    type: "reply",
    response: { text: "Здравствуйте", actions: [], pending: null, trace: [] },
  })
  s = reduceSession(s, { type: "send", text: "Что ты сделал?" })
  s = reduceSession(s, { type: "fail", text: ERROR_TEXT })
  assert.equal(s.busy, false)
  assert.equal(s.messages.length, 4)
  assert.deepEqual(s.messages[3], { role: "error", text: ERROR_TEXT })
  assert.equal(s.messages[0].text, "Привет")
})
