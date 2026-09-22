import { expect, test } from "@playwright/test"

for (const role of ["supervisor", "crew", "citizen", "unknown", "admin"]) {
  for (const width of [390, 1440]) {
    test(`${role}: menu at ${width}px`, async ({ page }) => {
      const errors: string[] = []
      page.on("pageerror", (error) => errors.push(error.message))
      page.on("console", (message) => {
        if (["error", "warning"].includes(message.type())) {
          errors.push(message.text())
        }
      })
      await page.setViewportSize({ width, height: 900 })
      await page.addInitScript(() => {
        localStorage.setItem("access_token", "c0-offline-token")
      })
      await page.route("**/api/v1/**", async (route) => {
        if (new URL(route.request().url()).pathname !== "/api/v1/users/me") {
          await route.abort()
          return
        }
        await route.fulfill({
          json: {
            id: "00000000-0000-0000-0000-000000000001",
            email: "c0@example.com",
            full_name: "C0 user",
            role,
            crew_id: role === "crew" ? "c1" : null,
            is_superuser: role === "admin",
            is_active: true,
          },
        })
      })
      await page.goto("/")
      await expect(page.getByRole("heading", { name: "Карта" })).toBeVisible()
      if (width === 390) {
        await page.getByRole("button", { name: "Collapse Sidebar" }).click()
      }
      await expect(page.getByTestId("user-menu")).toBeVisible()
      if (width === 390) {
        for (const button of await page
          .locator('[data-slot="sidebar-menu-button"]')
          .all()) {
          const box = await button.boundingBox()
          expect(box?.height).toBeGreaterThanOrEqual(48)
          expect(box?.width).toBeGreaterThanOrEqual(48)
        }
      }
      for (const label of ["Карта", "Очередь", "План и бригады"]) {
        await expect(
          page.getByRole("link", { name: label, exact: true }),
        ).toHaveCount(role === "supervisor" || role === "admin" ? 1 : 0)
      }
      await expect(
        page.getByRole("link", { name: "Мой маршрут", exact: true }),
      ).toHaveCount(role === "crew" || role === "admin" ? 1 : 0)
      await expect(
        page.getByRole("link", { name: "Admin", exact: true }),
      ).toHaveCount(role === "admin" ? 1 : 0)
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBe(true)
      expect(errors).toEqual([])
    })
  }
}

for (const state of ["loading", "empty", "unauthorized"]) {
  test(`current user: ${state}`, async ({ page }) => {
    await page.addInitScript(() => {
      if (!sessionStorage.getItem("c0-initialized")) {
        localStorage.setItem("access_token", "c0-offline-token")
        sessionStorage.setItem("c0-initialized", "true")
      }
    })
    let release: () => void = () => {}
    const pending = new Promise<void>((resolve) => {
      release = resolve
    })
    await page.route("**/api/v1/users/me", async (route) => {
      if (state === "loading") await pending
      await route.fulfill({
        status: state === "unauthorized" ? 401 : 200,
        json: state === "unauthorized" ? { detail: "Not authenticated" } : null,
      })
    })
    await page.goto("/")
    if (state === "unauthorized") {
      await expect(page).toHaveURL(/\/login$/, { timeout: 15000 })
      await expect(page.getByTestId("email-input")).toBeVisible()
      expect(
        await page.evaluate(() => localStorage.getItem("access_token")),
      ).toBeNull()
    } else {
      await expect(page.getByRole("heading", { name: "Карта" })).toBeVisible()
      await expect(
        page.getByRole("link", { name: "Очередь", exact: true }),
      ).toHaveCount(0)
    }
    release()
  })
}
test("mobile controls meet C0 target size", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 })
  await page.addInitScript(() =>
    localStorage.setItem("access_token", "c0-offline-token"),
  )
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({ json: null }),
  )
  await page.goto("/")
  const size = await page
    .getByRole("button", { name: "Collapse Sidebar" })
    .evaluate((element) => {
      const rect = element.getBoundingClientRect()
      return { width: rect.width, height: rect.height }
    })
  expect(size.width).toBeGreaterThanOrEqual(48)
  expect(size.height).toBeGreaterThanOrEqual(48)
})
