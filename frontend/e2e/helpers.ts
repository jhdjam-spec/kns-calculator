import { expect, type Page, type ConsoleMessage } from "@playwright/test";

/**
 * Shared helpers for E2E tests of KNS Calculator on LIVE YC deployment.
 */

/** Attach console error / pageerror listeners and return mutable array. */
export function collectPageErrors(page: Page): { errors: string[] } {
  const errors: string[] = [];

  page.on("pageerror", (err) => {
    errors.push(`pageerror: ${err.message}`);
  });

  page.on("console", (msg: ConsoleMessage) => {
    if (msg.type() === "error") {
      const text = msg.text();
      // Игнорируем шумные сторонние ошибки (favicon 404, hydration mismatch warnings)
      if (
        text.includes("favicon") ||
        text.includes("Failed to load resource: net::ERR_") ||
        // Известный шум от Tanstack Query devtools, не относится к функциональности
        text.includes("React Query Devtools")
      ) {
        return;
      }
      errors.push(`console.error: ${text}`);
    }
  });

  return { errors };
}

/** Verifies skip-link is present in DOM (sr-only by default). */
export async function checkSkipLink(page: Page): Promise<void> {
  const link = page.locator('a[href="#main"]');
  await expect(link, "skip-link [href=\"#main\"] должен присутствовать").toHaveCount(1);
}

/** Ensures page has non-empty <title>. */
export async function checkTitle(page: Page): Promise<string> {
  const title = await page.title();
  expect(title.length, "title не должен быть пустым").toBeGreaterThan(0);
  return title;
}

/** Validate response status for navigation. */
export async function checkRouteOk(page: Page, path: string): Promise<void> {
  const res = await page.goto(path, { waitUntil: "domcontentloaded" });
  expect(res, `goto(${path}) returned null response`).not.toBeNull();
  const status = res!.status();
  expect(status, `HTTP status for ${path}`).toBeLessThan(400);
}

export const ROUTES = {
  home: "/",
  project: "/project",
  tanks: "/tanks",
  storm: "/storm/minimal",
  teach: "/teach",
  teachTopic: (slug: string) => `/teach/${slug}`,
};

export const TEACH_TOPICS = [
  "water",
  "fire",
  "electrical",
  "hydraulics",
  "structural",
  "los",
];
