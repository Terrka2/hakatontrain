import { defineConfig } from "@playwright/test"

export default defineConfig({
  testDir: "./tests/c0",
  outputDir: "../test-results/c0",
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5174",
    channel: "msedge",
  },
  webServer: {
    command: "npx --yes bun run dev --host 127.0.0.1 --port 5174",
    url: "http://127.0.0.1:5174",
    reuseExistingServer: false,
  },
})
