// Тесты F6 на критерии приёмки. Запуск: node --test src/theme/theme.test.ts (без сети, без браузера).
import assert from "node:assert/strict"
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"
import { test } from "node:test"

import { CATEGORIES, categoryInfo } from "./categories.ts"
import { PRIORITY, priorityLevel } from "./priority.ts"

const FRONTEND = join(import.meta.dirname, "../..")
const demo = JSON.parse(
  readFileSync(join(FRONTEND, "src/mocks/demo_city.json"), "utf8"),
)
const css = readFileSync(join(FRONTEND, "src/index.css"), "utf8")

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name)
    return statSync(p).isDirectory() ? walk(p) : [p]
  })
}

/** oklch(L C H) → относительная яркость sRGB (WCAG). */
function luminance(oklch: string): number {
  const m = /oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)/.exec(oklch)
  assert.ok(m, `не oklch: ${oklch}`)
  const [L, C, H] = [Number(m[1]), Number(m[2]), (Number(m[3]) * Math.PI) / 180]
  const a = C * Math.cos(H)
  const b = C * Math.sin(H)
  const l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
  const m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
  const s_ = (L - 0.0894841775 * a - 1.291485548 * b) ** 3
  const lin = [
    4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
    -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
    -0.0041960863 * l_ - 0.7034186147 * m_ + 1.707614701 * s_,
  ].map((v) => Math.min(1, Math.max(0, v)))
  return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
}

function contrast(bg: string, fg: string): number {
  const [a, b] = [luminance(bg), luminance(fg)].sort((x, y) => y - x)
  return (a + 0.05) / (b + 0.05)
}

function tokens(block: ":root" | ".dark"): Record<string, string> {
  const start = css.indexOf(`${block} {`)
  const end = css.indexOf("\n}", start)
  const out: Record<string, string> = {}
  for (const m of css.slice(start, end).matchAll(/--([\w-]+):\s*([^;]+);/g))
    out[m[1]] = m[2].trim()
  return out
}

test("критерий 1: в features/** нет цветов мимо токенов", () => {
  const bad = walk(join(FRONTEND, "src/features"))
    .filter((f) => /\.(tsx?|css)$/.test(f))
    .filter((f) => /#[0-9a-fA-F]{3,6}\b|rgb\(/.test(readFileSync(f, "utf8")))
  assert.deepEqual(bad, [])
})

test("критерий 2: контраст текста на бейджах приоритета ≥ 4.5 в обеих темах", () => {
  for (const theme of [":root", ".dark"] as const) {
    const t = tokens(theme)
    for (const level of ["high", "mid", "low"]) {
      const ratio = contrast(
        t[`priority-${level}`],
        t[`priority-${level}-foreground`],
      )
      assert.ok(
        ratio >= 4.5,
        `${theme} priority-${level}: контраст ${ratio.toFixed(2)}`,
      )
    }
  }
})

test("критерий 3: у каждой категории из fixture есть иконка и подпись RU", () => {
  const cats = new Set<string>(
    demo.reports.map((r: { category: string }) => r.category),
  )
  for (const c of cats) {
    const info = CATEGORIES[c]
    assert.ok(info, `нет категории ${c}`)
    assert.match(info.label, /[а-яё]/i, `подпись не на русском: ${c}`)
    assert.ok(info.icon, `нет иконки: ${c}`)
  }
  assert.equal(categoryInfo("  Pothole ").label, CATEGORIES.pothole.label)
  assert.equal(categoryInfo(null).label, "Другое")
})

test("ступени приоритета согласованы с fixture.expect", () => {
  assert.equal(priorityLevel(demo.expect.min_score_manhole), "high")
  assert.equal(priorityLevel(demo.expect.min_score_school_pothole), "high")
  assert.equal(priorityLevel(demo.expect.max_score_low_noise), "low")
  assert.equal(priorityLevel(55), "mid")
  assert.equal(PRIORITY[priorityLevel(0)].label, PRIORITY.low.label)
})

test("токены приоритета, бригад и статусов есть в обеих темах", () => {
  const names = [
    "priority-high",
    "priority-mid",
    "priority-low",
    "crew-1",
    "crew-2",
    "crew-3",
    "status-open",
    "status-planned",
    "status-in-progress",
    "status-resolved",
  ]
  for (const theme of [":root", ".dark"] as const) {
    const t = tokens(theme)
    for (const n of names) assert.ok(t[n], `${theme}: нет --${n}`)
  }
})
