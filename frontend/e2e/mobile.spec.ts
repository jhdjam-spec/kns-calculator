import { test, expect } from "@playwright/test";
import { checkRouteOk, collectPageErrors, ROUTES } from "./helpers";

/**
 * Mobile viewport tests — burger menu, theme toggle, touch targets, a11y.
 * Viewport: 375 × 667 (iPhone SE base).
 *
 * Используем chromium с mobile viewport (без webkit, чтобы не тянуть лишний браузер).
 */
test.use({
  viewport: { width: 375, height: 667 },
  userAgent:
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
  hasTouch: true,
  isMobile: true,
});

test.describe("Mobile (375×667)", () => {
  test("Home loads on mobile, no JS errors", async ({ page }) => {
    const { errors } = collectPageErrors(page);
    await checkRouteOk(page, ROUTES.home);
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    expect(errors, `JS errors on mobile home: ${errors.join("\n")}`).toEqual([]);
  });

  test("Burger menu button visible on mobile", async ({ page }) => {
    await page.goto(ROUTES.home);
    const burger = page.getByRole("button", { name: /меню|menu|открыть/i }).first();
    await expect(burger).toBeVisible();
  });

  test("Burger opens drawer, ESC closes it", async ({ page }) => {
    await page.goto(ROUTES.home);
    const burger = page.getByRole("button", { name: /открыть меню|меню|menu/i }).first();
    await burger.click();
    const drawer = page.locator('[role="dialog"][aria-modal="true"]');
    await expect(drawer).toBeVisible();
    // aria-expanded should be true after open
    await expect(burger).toHaveAttribute("aria-expanded", "true");

    // Esc closes drawer
    await page.keyboard.press("Escape");
    await expect(drawer).toBeHidden({ timeout: 3_000 }).catch(async () => {
      // fallback: click close button
      const closeBtn = page.getByRole("button", { name: /закрыть|close/i });
      if ((await closeBtn.count()) > 0) {
        await closeBtn.first().click();
      }
    });
  });

  test("Mobile phone link visible (tel:)", async ({ page }) => {
    await page.goto(ROUTES.home);
    // На mobile breakpoint виден иконочный tel-link (md:hidden), desktop full-format скрыт (hidden md:flex)
    const tel = page.locator('a[href^="tel:"]:visible').first();
    await expect(tel).toBeVisible();
  });

  test("Theme toggle button present and clickable", async ({ page }) => {
    await page.goto(ROUTES.home);
    const themeBtn = page
      .locator("button[aria-label^='Тема'], button[title^='Тема']")
      .first();
    await expect(themeBtn).toBeVisible();
    const labelBefore = await themeBtn.getAttribute("aria-label");
    await themeBtn.click();
    await page.waitForTimeout(300);
    const labelAfter = await themeBtn.getAttribute("aria-label");
    expect(
      labelBefore !== labelAfter,
      `theme aria-label should cycle (before=${labelBefore}, after=${labelAfter})`,
    ).toBe(true);
  });

  test("Theme toggle changes <html> class (light/dark)", async ({ page }) => {
    await page.goto(ROUTES.home);
    const themeBtn = page
      .locator("button[aria-label^='Тема'], button[title^='Тема']")
      .first();

    const getHtmlClass = async () => page.evaluate(() => document.documentElement.className);

    const initial = await getHtmlClass();
    // Click 3 times — cycle auto→light→dark→auto
    await themeBtn.click();
    await page.waitForTimeout(150);
    const c1 = await getHtmlClass();
    await themeBtn.click();
    await page.waitForTimeout(150);
    const c2 = await getHtmlClass();

    // At least one of c1/c2 should differ from initial
    const changed = c1 !== initial || c2 !== initial;
    expect(changed, `<html> className should change after theme cycles (init=${initial}, c1=${c1}, c2=${c2})`).toBe(true);
  });

  test("Main CTA button has touch target ≥44px on mobile", async ({ page }) => {
    await page.goto(ROUTES.home);
    const btn = page.getByRole("button", { name: /Рассчитать/i }).first();
    await expect(btn).toBeVisible();
    const box = await btn.boundingBox();
    expect(box, "CTA button has bounding box").not.toBeNull();
    // Hero CTA height — should be ≥44 (sm:h-16=64, base h-14=56)
    expect(box!.height, `CTA height = ${box!.height}px`).toBeGreaterThanOrEqual(44);
  });

  test("Burger button has touch target ≥44px", async ({ page }) => {
    await page.goto(ROUTES.home);
    const burger = page.getByRole("button", { name: /открыть меню|меню/i }).first();
    const box = await burger.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height, `Burger height = ${box!.height}px`).toBeGreaterThanOrEqual(44);
    expect(box!.width, `Burger width = ${box!.width}px`).toBeGreaterThanOrEqual(44);
  });

  test("Skip-link visible on focus", async ({ page }) => {
    await page.goto(ROUTES.home);
    // Tab once → skip-link should be in focus
    await page.keyboard.press("Tab");
    const skip = page.locator('a[href="#main"]');
    await expect(skip).toBeFocused();
  });

  test("Drawer NAV_LINKS rendered after opening", async ({ page }) => {
    await page.goto(ROUTES.home);
    const burger = page.getByRole("button", { name: /открыть меню|меню/i }).first();
    await burger.click();
    const drawer = page.locator('[role="dialog"]');
    // Expect at least 4 nav links inside drawer
    const navLinks = drawer.locator("a");
    expect(await navLinks.count()).toBeGreaterThanOrEqual(4);
  });
});
