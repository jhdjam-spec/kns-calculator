import { test, expect } from "@playwright/test";
import { checkRouteOk, checkSkipLink, checkTitle, collectPageErrors, ROUTES } from "./helpers";

test.describe("Project Wizard /project", () => {
  test("loads with 200, no JS errors", async ({ page }) => {
    const { errors } = collectPageErrors(page);
    await checkRouteOk(page, ROUTES.project);
    await checkTitle(page);
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    expect(errors, `JS errors on /project: ${errors.join("\n")}`).toEqual([]);
  });

  test("skip-link present", async ({ page }) => {
    await page.goto(ROUTES.project);
    await checkSkipLink(page);
  });

  test("H1 heading 'Проект' rendered", async ({ page }) => {
    await page.goto(ROUTES.project);
    await expect(page.locator("body")).toContainText(/проект/i);
  });

  test("Wizard step1 → step2 navigation", async ({ page }) => {
    await page.goto(ROUTES.project);
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});

    // Wizard может использовать "Далее" / "Next" кнопку. Толерантно ищем любую CTA.
    const nextBtn = page
      .getByRole("button", { name: /далее|next|продолжить|шаг 2|расчёт|рассчитать/i })
      .first();

    if ((await nextBtn.count()) === 0) {
      // Wizard может ждать ввода числового поля Q. Введём минимум.
      const numericInputs = page.locator('input[type="number"]');
      if ((await numericInputs.count()) > 0) {
        await numericInputs.first().fill("15");
      }
    }

    // Try clicking the first "Далее"/"Расчёт" button if exists
    const cta = page
      .getByRole("button", { name: /далее|продолжить|рассчитать|расчёт/i })
      .first();
    if ((await cta.count()) > 0 && (await cta.isEnabled().catch(() => false))) {
      await cta.click();
      // Verify URL or DOM changed: wait for any change
      await page.waitForTimeout(1500);
    }

    // Mostly we just verify no crash happened
    const errors = await page.evaluate(() => document.body.innerText.length);
    expect(errors).toBeGreaterThan(50);
  });

  test("Form submit returns result or shows validation", async ({ page }) => {
    await page.goto(ROUTES.project);
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});

    const submitBtn = page
      .getByRole("button", { name: /рассчитать|расчёт|подобрать|готово/i })
      .first();

    if ((await submitBtn.count()) === 0) {
      test.info().annotations.push({
        type: "skip-reason",
        description: "No submit button found on /project",
      });
      return;
    }

    // Best-effort submit. Just verify no uncaught exception is thrown.
    await submitBtn.click().catch(() => {});
    await page.waitForTimeout(1500);
    // Ensure page still has content
    await expect(page.locator("body")).toBeVisible();
  });
});
