import { defineConfig } from "@playwright/test";

/**
 * Prototype recording config for the workout logging flow (#10).
 *
 * Start the prototype web app from this worktree on port 3001 and keep the API
 * on :8000, then run:
 *
 *   pnpm exec playwright test e2e/record-workout-logging.spec.ts
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  outputDir: "test-results/workout-logging",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3001",
    viewport: { width: 1440, height: 900 },
    video: {
      mode: "on",
      size: { width: 1440, height: 900 },
    },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    actionTimeout: 20_000,
  },
});
