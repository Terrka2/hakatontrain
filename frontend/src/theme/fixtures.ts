import fs from "node:fs"
import path from "node:path"

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

export interface DemoCityFixture {
  now: string
  reports: Array<{
    id: string
    category: string
    text: string
    [key: string]: unknown
  }>
  expect?: Record<string, unknown>
}

export function loadDemoCityFixture(): DemoCityFixture {
  const repoRoot = getRepoRoot()
  const fixturePath = path.join(
    repoRoot,
    "backend",
    "app",
    "fixtures",
    "demo_city.json",
  )
  const content = fs.readFileSync(fixturePath, "utf-8")
  return JSON.parse(content) as DemoCityFixture
}

export function getCategoriesFromFixture(): string[] {
  const fixture = loadDemoCityFixture()
  const categories = new Set<string>()
  for (const report of fixture.reports) {
    if (report.category) {
      categories.add(report.category)
    }
  }
  return Array.from(categories)
}

