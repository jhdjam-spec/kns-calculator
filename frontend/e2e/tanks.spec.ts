import { test, expect } from "@playwright/test";
import { checkRouteOk, checkSkipLink, checkTitle, collectPageErrors, ROUTES } from "./helpers";

test.describe("Tanks page /tanks", () => {
  test("loads with 200, no JS errors", async ({ page }) => {
    const { errors } = collectPageErrors(page);
    await checkRouteOk(page, ROUTES.tanks);
    await checkTitle(page);
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    expect(errors, `JS errors on /tanks: ${errors.join("\n")}`).toEqual([]);
  });

  test("skip-link present", async ({ page }) => {
    await page.goto(ROUTES.tanks);
    await checkSkipLink(page);
  });

  test("3 tabs: ПП, КНС, Стеклопластик", async ({ page }) => {
    await page.goto(ROUTES.tanks);
    const tabs = page.locator('[role="tab"]');
    await expect(tabs).toHaveCount(3);
  });

  test("Tab switch: КНС tab is selectable", async ({ page }) => {
    await page.goto(ROUTES.tanks);
    const knsTab = page.locator('[role="tab"]').filter({ hasText: /КНС/i }).first();
    await expect(knsTab).toBeVisible();
    await knsTab.click();
    await expect(knsTab).toHaveAttribute("aria-selected", "true");
  });

  test("Tab switch: Стеклопластик shows 'В разработке'", async ({ page }) => {
    await page.goto(ROUTES.tanks);
    const fbTab = page.locator('[role="tab"]').filter({ hasText: /стеклопласт/i }).first();
    await fbTab.click();
    await expect(page.locator("body")).toContainText(/в разработке|разработке/i);
  });

  test("Tank form has number inputs", async ({ page }) => {
    await page.goto(ROUTES.tanks);
    const numInputs = page.locator('input[type="number"]');
    expect(await numInputs.count()).toBeGreaterThan(0);
  });
});
