import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { describe, it } from "node:test"
import { getCategoriesFromFixture } from "./fixtures"

// WCAG 2.1 relative luminance and contrast calculation without external dependencies
function parseColorToRgb(colorStr: string): [number, number, number] {
  const trimmed = colorStr.trim()
  if (trimmed.startsWith("#")) {
    const raw = trimmed.slice(1)
    if (raw.length === 3) {
      return [
        parseInt(raw[0] + raw[0], 16),
        parseInt(raw[1] + raw[1], 16),
        parseInt(raw[2] + raw[2], 16),
      ]
    }
    if (raw.length === 6) {
      return [
        parseInt(raw.slice(0, 2), 16),
        parseInt(raw.slice(2, 4), 16),
        parseInt(raw.slice(4, 6), 16),
      ]
    }
  }

  const rgbMatch = trimmed.match(/rgba?\((\d+)[,\s]+(\d+)[,\s]+(\d+)/)
  if (rgbMatch) {
    return [
      parseInt(rgbMatch[1], 10),
      parseInt(rgbMatch[2], 10),
      parseInt(rgbMatch[3], 10),
    ]
  }

  const oklchMatch = trimmed.match(/oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)/)
  if (oklchMatch) {
    const L = parseFloat(oklchMatch[1])
    const C = parseFloat(oklchMatch[2])
    const hDeg = parseFloat(oklchMatch[3])
    const hRad = (hDeg * Math.PI) / 180
    const a = C * Math.cos(hRad)
    const b = C * Math.sin(hRad)

    const l_ = L + 0.3963377774 * a + 0.2158037573 * b
    const m_ = L - 0.1055613458 * a - 0.0638541728 * b
    const s_ = L - 0.0894841775 * a - 1.291485548 * b
    const l = l_ * l_ * l_
    const m = m_ * m_ * m_
    const s = s_ * s_ * s_
    const rLin = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    const gLin = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    const bLin = -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s
    const toSrgb = (c: number) => {
      const clamped = Math.max(0, Math.min(1, c))
      return clamped <= 0.0031308
        ? clamped * 12.92
        : 1.055 * clamped ** (1 / 2.4) - 0.055
    }
    return [
      Math.round(toSrgb(rLin) * 255),
      Math.round(toSrgb(gLin) * 255),
      Math.round(toSrgb(bLin) * 255),
    ]
  }

  throw new Error(`Unsupported color format for contrast testing: ${colorStr}`)
}

function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs
}

function getContrastRatio(color1: string, color2: string): number {
  const [r1, g1, b1] = parseColorToRgb(color1)
  const [r2, g2, b2] = parseColorToRgb(color2)
  const l1 = getLuminance(r1, g1, b1)
  const l2 = getLuminance(r2, g2, b2)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

function getRepoRoot(): string {
  let curr = __dirname
  while (!fs.existsSync(path.join(curr, "docs", "contracts", "F6_design.md"))) {
    const parent = path.dirname(curr)
    if (parent === curr) {
      throw new Error("Could not find repository root")
    }
    curr = parent
  }
  return curr
}

describe("F6 Design System - L0 Acceptance Criteria", () => {
  const repoRoot = getRepoRoot()

  // Criterion 1: Ни в одном файле frontend/src/features/** нет цвета в виде #hex или rgb( — только токены
  it("Criterion 1: No raw #hex or rgb( colors in frontend/src/features/** and theme tokens defined", async () => {
    // 1. Theme priority and tokens must be defined and exported
    const priorityModule = await import("./priority")
    const hasTokens =
      (priorityModule as Record<string, unknown>).PRIORITY_BADGES ||
      (priorityModule as Record<string, unknown>).PRIORITY_COLORS ||
      (priorityModule as Record<string, unknown>).priorityColors
    assert.ok(
      hasTokens,
      "frontend/src/theme/priority.ts must export color tokens (PRIORITY_BADGES / PRIORITY_COLORS)",
    )

    // 2. Scan features for any raw color violations
    const featuresDir = path.join(repoRoot, "frontend", "src", "features")
    const violations: { file: string; line: number; match: string }[] = []

    function scanDir(dir: string) {
      if (!fs.existsSync(dir)) return
      const entries = fs.readdirSync(dir, { withFileTypes: true })
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name)
        if (entry.isDirectory()) {
          scanDir(fullPath)
        } else if (/\.(tsx?|jsx?|css)$/.test(entry.name)) {
          const content = fs.readFileSync(fullPath, "utf-8")
          const lines = content.split("\n")
          lines.forEach((lineText, idx) => {
            const codeOnly = lineText
              .replace(/\/\/.*$/, "")
              .replace(/\/\*.*?\*\//g, "")
            const hexMatch = codeOnly.match(/#[0-9a-fA-F]{3,8}\b/)
            const rgbMatch = codeOnly.match(/rgba?\(/)
            if (hexMatch) {
              violations.push({
                file: path.relative(repoRoot, fullPath),
                line: idx + 1,
                match: hexMatch[0],
              })
            }
            if (rgbMatch) {
              violations.push({
                file: path.relative(repoRoot, fullPath),
                line: idx + 1,
                match: rgbMatch[0],
              })
            }
          })
        }
      }
    }

    scanDir(featuresDir)
    assert.strictEqual(
      violations.length,
      0,
      `Found ${violations.length} raw color occurrences in features:\n` +
        violations.map((v) => `  ${v.file}:${v.line} -> ${v.match}`).join("\n"),
    )
  })

  // Criterion 2: Контраст текста на бейджах приоритета ≥ 4.5:1 в обеих темах
  it("Criterion 2: Text contrast on priority badges is >= 4.5:1 in both light and dark themes", async () => {
    const priorityModule = await import("./priority")
    const priorityBadges =
      (priorityModule as Record<string, unknown>).PRIORITY_BADGES ||
      (priorityModule as Record<string, unknown>).PRIORITY_COLORS ||
      (priorityModule as Record<string, unknown>).priorityColors

    assert.ok(
      priorityBadges && typeof priorityBadges === "object",
      "frontend/src/theme/priority.ts must export PRIORITY_BADGES or PRIORITY_COLORS",
    )

    const levels = ["high", "medium", "low"]
    const badgesObj = priorityBadges as Record<string, unknown>

    for (const level of levels) {
      assert.ok(
        badgesObj[level],
        `priority theme must include definition for level '${level}'`,
      )

      const levelDef = badgesObj[level] as {
        light?: { bg: string; text: string }
        dark?: { bg: string; text: string }
      }

      assert.ok(
        levelDef.light?.bg && levelDef.light?.text,
        `Level '${level}' missing light theme colors`,
      )
      assert.ok(
        levelDef.dark?.bg && levelDef.dark?.text,
        `Level '${level}' missing dark theme colors`,
      )

      const lightRatio = getContrastRatio(
        levelDef.light.bg,
        levelDef.light.text,
      )
      assert.ok(
        lightRatio >= 4.5,
        `Priority '${level}' light theme contrast is ${lightRatio.toFixed(2)}:1, must be >= 4.5:1`,
      )

      const darkRatio = getContrastRatio(levelDef.dark.bg, levelDef.dark.text)
      assert.ok(
        darkRatio >= 4.5,
        `Priority '${level}' dark theme contrast is ${darkRatio.toFixed(2)}:1, must be >= 4.5:1`,
      )
    }
  })

  // Criterion 3: Каждая категория имеет иконку и подпись RU
  it("Criterion 3: Every canonical category has an icon and Russian label", async () => {
    // Categories extracted from backend/app/fixtures/demo_city.json
    const fixtureCategories = getCategoriesFromFixture()
    assert.ok(
      fixtureCategories.length > 0,
      "Expected categories to be extracted from demo_city.json fixture",
    )

    // CategoryIcon component must be exported from frontend/src/components/ui/CategoryIcon
    const catIconModulePath = "../components/ui/CategoryIcon"
    const catIconMod = (await (
      import(catIconModulePath as string) as Promise<unknown>
    ).catch(() => null)) as Record<string, unknown> | null

    assert.ok(
      catIconMod && (catIconMod.CategoryIcon || catIconMod.CATEGORY_CONFIG),
      "frontend/src/components/ui/CategoryIcon must exist and export CategoryIcon component or CATEGORY_CONFIG",
    )

    const categoryConfig = (catIconMod?.CATEGORY_CONFIG ||
      ((await import("./priority").catch(() => ({}))) as Record<string, unknown>)
        .CATEGORY_CONFIG) as Record<string, { label: string; icon: unknown }> | null

    assert.ok(
      categoryConfig && typeof categoryConfig === "object",
      "CATEGORY_CONFIG must be defined with Russian labels and icons",
    )

    for (const cat of fixtureCategories) {
      assert.ok(categoryConfig[cat], `Missing category config for fixture category '${cat}'`)
      const item = categoryConfig[cat]
      const labelText: string = item.label
      const iconComp: unknown = item.icon
      assert.ok(
        typeof labelText === "string" && labelText.length > 0,
        `Category '${cat}' missing RU label`,
      )
      assert.match(
        labelText,
        /[а-яА-ЯёЁ]/,
        `Category '${cat}' label '${labelText}' must contain Russian Cyrillic characters`,
      )
      assert.ok(iconComp, `Category '${cat}' missing icon component`)
    }
  })

  // Criterion 4: docs/design/review.md существует и содержит ≥10 замечаний
  it("Criterion 4: docs/design/review.md contains at least 10 reviewed items", () => {
    const reviewPath = path.join(repoRoot, "docs", "design", "review.md")
    assert.ok(
      fs.existsSync(reviewPath),
      "docs/design/review.md must exist in the repository",
    )

    const content = fs.readFileSync(reviewPath, "utf-8")

    // Count list items (lines starting with - or 1., 2. etc.)
    const listItems = content
      .split("\n")
      .map((l) => l.trim())
      .filter((line) => /^-\s+/.test(line) || /^\d+\.\s+/.test(line))

    assert.ok(
      listItems.length >= 10,
      `docs/design/review.md must contain at least 10 review items, found ${listItems.length}`,
    )
  })
})
