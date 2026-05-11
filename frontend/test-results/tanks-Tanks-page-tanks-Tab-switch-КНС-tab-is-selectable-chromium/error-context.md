# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: tanks.spec.ts >> Tanks page /tanks >> Tab switch: КНС tab is selectable
- Location: e2e\tanks.spec.ts:24:7

# Error details

```
TimeoutError: page.goto: Timeout 20000ms exceeded.
Call log:
  - navigating to "https://kns-calculator-frontend.website.yandexcloud.net/tanks", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from "@playwright/test";
  2  | import { checkRouteOk, checkSkipLink, checkTitle, collectPageErrors, ROUTES } from "./helpers";
  3  | 
  4  | test.describe("Tanks page /tanks", () => {
  5  |   test("loads with 200, no JS errors", async ({ page }) => {
  6  |     const { errors } = collectPageErrors(page);
  7  |     await checkRouteOk(page, ROUTES.tanks);
  8  |     await checkTitle(page);
  9  |     await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
  10 |     expect(errors, `JS errors on /tanks: ${errors.join("\n")}`).toEqual([]);
  11 |   });
  12 | 
  13 |   test("skip-link present", async ({ page }) => {
  14 |     await page.goto(ROUTES.tanks);
  15 |     await checkSkipLink(page);
  16 |   });
  17 | 
  18 |   test("3 tabs: ПП, КНС, Стеклопластик", async ({ page }) => {
  19 |     await page.goto(ROUTES.tanks);
  20 |     const tabs = page.locator('[role="tab"]');
  21 |     await expect(tabs).toHaveCount(3);
  22 |   });
  23 | 
  24 |   test("Tab switch: КНС tab is selectable", async ({ page }) => {
> 25 |     await page.goto(ROUTES.tanks);
     |                ^ TimeoutError: page.goto: Timeout 20000ms exceeded.
  26 |     const knsTab = page.locator('[role="tab"]').filter({ hasText: /КНС/i }).first();
  27 |     await expect(knsTab).toBeVisible();
  28 |     await knsTab.click();
  29 |     await expect(knsTab).toHaveAttribute("aria-selected", "true");
  30 |   });
  31 | 
  32 |   test("Tab switch: Стеклопластик shows 'В разработке'", async ({ page }) => {
  33 |     await page.goto(ROUTES.tanks);
  34 |     const fbTab = page.locator('[role="tab"]').filter({ hasText: /стеклопласт/i }).first();
  35 |     await fbTab.click();
  36 |     await expect(page.locator("body")).toContainText(/в разработке|разработке/i);
  37 |   });
  38 | 
  39 |   test("Tank form has number inputs", async ({ page }) => {
  40 |     await page.goto(ROUTES.tanks);
  41 |     const numInputs = page.locator('input[type="number"]');
  42 |     expect(await numInputs.count()).toBeGreaterThan(0);
  43 |   });
  44 | });
  45 | 
```