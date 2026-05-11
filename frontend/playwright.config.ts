import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E config for KNS Calculator frontend.
 * Тестируем LIVE deployment на Yandex Cloud Object Storage.
 *
 * Run: `npx playwright test --reporter=line`
 */

const BASE_URL =
  process.env.E2E_BASE_URL ||
  "https://kns-calculator-frontend.website.yandexcloud.net";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 7_000 },
  fullyParallel: true,
  retries: 1,
  workers: 4,
  reporter: [["line"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL: BASE_URL,
    headless: true,
    ignoreHTTPSErrors: true,
    actionTimeout: 7_000,
    navigationTimeout: 20_000,
    viewport: { width: 1280, height: 800 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    extraHTTPHeaders: {
      "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
