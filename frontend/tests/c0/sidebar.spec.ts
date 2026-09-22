import { expect, test } from "@playwright/test"

for (const role of ["supervisor", "crew", "citizen", "unknown", "admin"]) {
  for (const width of [390, 1440]) {
    test(`${role}: menu at ${width}px`, async ({ page }) => {
      const errors: string[] = []
      page.on("pageerror", (error) => errors.push(error.message))
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
