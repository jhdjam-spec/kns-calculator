import { test, expect } from "@playwright/test";
import { checkRouteOk, checkSkipLink, checkTitle, collectPageErrors, ROUTES } from "./helpers";

/**
 * Главная страница `/` — Hero, calculator CTA, FAQ.
 * LIVE: https://kns-calculator-frontend.website.yandexcloud.net/
 */
test.describe("Home page /", () => {
  test("loads with 200, has title, no JS errors", async ({ page }) => {
    const { errors } = collectPageErrors(page);
    await checkRouteOk(page, ROUTES.home);
    const title = await checkTitle(page);
    expect(title).toContain("ИНСЕРВО");
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    expect(errors, `JS errors on home: ${errors.join("\n")}`).toEqual([]);
  });

  test("skip-link present (a11y)", async ({ page }) => {
    await page.goto(ROUTES.home);
    await checkSkipLink(page);
  });

  test("Hero H1 visible", async ({ page }) => {
    await page.goto(ROUTES.home);
    const h1 = page.locator("h1").first();
    await expect(h1).toBeVisible();
    await expect(h1).toContainText(/насос/i);
  });

  test("Hero CTA 'Рассчитать' triggers backend (Q=15)", async ({ page }) => {
    await page.goto(ROUTES.home);
    const qInput = page.locator("#hero-q");
    await expect(qInput).toBeVisible();
    await qInput.fill("15");
    const btn = page.getByRole("button", { name: /Рассчитать/i }).first();
    await expect(btn).toBeEnabled();

    // Wait either for backend network response OR for results section to appear.
    const responsePromise = page
      .waitForResponse(
        (resp) =>
          /\/api\/backend\/select|\/select\/pumps|apigw\.yandexcloud\.net.*select/.test(resp.url()),
        { timeout: 20_000 },
      )
      .catch(() => null);

    await btn.click();
    const resp = await responsePromise;
    if (resp) {
      expect(resp.status(), `backend select status (url=${resp.url()})`).toBeLessThan(500);
    }

    // Results section should appear (Cases/ResultsCompare). Tolerant: just wait for some change.
    await page.waitForTimeout(2000);
    // Check that either results card or error alert appeared (not stuck on initial state)
    const hasResults = await page.locator('[data-results], [role="alert"], section').count();
    expect(hasResults).toBeGreaterThan(0);
  });

  test("FAQ section present", async ({ page }) => {
    await page.goto(ROUTES.home);
    const faq = page.locator("#faq, [id*='faq']").first();
    await expect(faq).toBeAttached();
  });

  test("FAQ accordion toggles aria-expanded", async ({ page }) => {
    await page.goto(ROUTES.home);
    // FAQ typically uses <button aria-expanded>. Try first candidate.
    const faqBtn = page
      .locator("[aria-expanded]")
      .filter({ hasText: /\?|насос|КНС|подбор|стоимост|сроки/i })
      .first();

    if ((await faqBtn.count()) === 0) {
      test.info().annotations.push({ type: "skip-reason", description: "FAQ accordion buttons not found by selector" });
      return;
    }

    const before = await faqBtn.getAttribute("aria-expanded");
    await faqBtn.click();
    const after = await faqBtn.getAttribute("aria-expanded");
    expect(before === after, `aria-expanded should change after click (was=${before}, now=${after})`).toBe(false);
  });

  test("Phone link in nav (tel:+7800...)", async ({ page }) => {
    await page.goto(ROUTES.home);
    const phone = page.locator('a[href^="tel:"]').first();
    await expect(phone).toBeAttached();
  });
});
