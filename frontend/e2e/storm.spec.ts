import { test, expect } from "@playwright/test";
import { checkRouteOk, checkSkipLink, checkTitle, collectPageErrors, ROUTES } from "./helpers";

test.describe("Storm /storm/minimal", () => {
  test("loads with 200, has title, no JS errors", async ({ page }) => {
    const { errors } = collectPageErrors(page);
    await checkRouteOk(page, ROUTES.storm);
    const title = await checkTitle(page);
    expect(title).toMatch(/ливн|сток|минимал/i);
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    expect(errors, `JS errors on /storm/minimal: ${errors.join("\n")}`).toEqual([]);
  });

  test("skip-link present", async ({ page }) => {
    await page.goto(ROUTES.storm);
    await checkSkipLink(page);
  });

  test("Storm form rendered", async ({ page }) => {
    await page.goto(ROUTES.storm);
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    const numInputs = page.locator('input[type="number"], input[inputmode="numeric"], input[inputmode="decimal"]');
    expect(await numInputs.count()).toBeGreaterThan(0);
  });

  test("Mode toggle classical/minimal exists or upgrade notice shown", async ({ page }) => {
    await page.goto(ROUTES.storm);
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});

    // Поиск toggle между minimal/classical режимами (по тексту, role=button/radio/tab)
    const classicalBtn = page
      .locator("button, [role='tab'], [role='radio'], a")
      .filter({ hasText: /классич|classical|расширенн/i });

    if ((await classicalBtn.count()) === 0) {
      // Допустимо: страница только minimal. Просто проверяем что есть заголовок ливнёвки.
      await expect(page.locator("body")).toContainText(/ливн/i);
      return;
    }

    await classicalBtn.first().click();
    await page.waitForTimeout(800);
    const upgrade = page
      .locator("body")
      .filter({ hasText: /upgrade|расширенн|premium|про-режим|обнов|для проектировщиков/i });
    // Best-effort assertion
    expect(await upgrade.count()).toBeGreaterThan(0);
  });
});
