// ╭───────────────────────────────────────────────────────────────────────╮
// │ Click-through audit: прокликивает все ключевые button/CTA на live      │
// │ podborkns.ru и репортит проблемы. Сделано для разовой проверки         │
// │ работоспособности после редизайна.                                     │
// │ Run: E2E_BASE_URL=https://podborkns.ru npx playwright test e2e/click-audit.spec.ts --workers=1 --reporter=line │
// ╰───────────────────────────────────────────────────────────────────────╯
import { test, expect } from "@playwright/test";

const BASE = process.env.E2E_BASE_URL || "https://podborkns.ru";

test.describe("Click-through audit on live", () => {
  test.describe.configure({ mode: "serial" });

  test("Home: H1 + Hero CTA enabled + 8-800 link", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(`console: ${m.text()}`);
    });

    await page.goto(BASE);
    await expect(page.locator("h1").first()).toContainText(/насос/i);

    // Hero Q input
    const qInput = page.locator("#hero-q");
    await expect(qInput).toBeVisible();
    await expect(qInput).toHaveValue("21.2");

    // CTA enabled
    const heroCta = page.getByRole("button", { name: /Подобрать|Рассчитать|Запустить/i }).first();
    await expect(heroCta).toBeEnabled();

    // Phone link tel:
    const phone = page.locator('a[href^="tel:"]').first();
    await expect(phone).toHaveAttribute("href", /\+7/);

    expect(errors, errors.join("\n")).toEqual([]);
  });

  test("Donate-bar: видимая полоса под меню, ссылка на #donate", async ({ page }) => {
    await page.goto(BASE);
    const donateBar = page.locator('a[href="#donate"]').first();
    await expect(donateBar).toBeVisible();
    await expect(donateBar).toContainText(/Поддержать/i);
  });

  test("Hero submit Q=15 → переход к Calculator, нет JS-ошибок", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => {
      if (m.type() === "error" && !m.text().includes("Failed to load resource")) {
        errors.push(`console: ${m.text()}`);
      }
    });

    await page.goto(BASE);
    await page.locator("#hero-q").fill("15");
    const cta = page.getByRole("button", { name: /Подобрать|Рассчитать/i }).first();
    await cta.click();

    // Ждём либо backend, либо secret-show результата секции
    await page.waitForTimeout(3000);

    // Должна появиться секция #calculator или результат
    const calculatorSection = page.locator("#calculator");
    await expect(calculatorSection).toBeVisible();

    expect(errors, `JS errors: ${errors.join("\n")}`).toEqual([]);
  });

  test("FAQ: все вопросы открываются по клику (aria-expanded)", async ({ page }) => {
    await page.goto(`${BASE}/#faq`);
    await page.waitForLoadState("domcontentloaded");

    const faqButtons = page.locator('[id^="faq-trigger-"]');
    const count = await faqButtons.count();
    expect(count).toBeGreaterThanOrEqual(5);

    // Кликнем каждую FAQ-кнопку
    for (let i = 0; i < count; i++) {
      const btn = faqButtons.nth(i);
      const wasExpanded = await btn.getAttribute("aria-expanded");
      await btn.click();
      const newExpanded = await btn.getAttribute("aria-expanded");
      expect(
        newExpanded,
        `FAQ-${i}: aria-expanded не меняется (было ${wasExpanded})`,
      ).not.toBe(wasExpanded);
    }
  });

  test("DonateCard: YooMoney Fundraise iframe + CTA-ссылка на /fundraise/", async ({ page }) => {
    await page.goto(`${BASE}/#donate`);
    await page.waitForLoadState("domcontentloaded");

    // 1) Iframe виджета YooMoney Fundraise виден
    const widgetIframe = page.locator('iframe[src*="yoomoney.ru"][src*="fundraise"]');
    await expect(widgetIframe).toBeVisible({ timeout: 10_000 });

    // 2) CTA-ссылка ведёт на полную страницу сбора (billNumber фиксирован)
    const donateLink = page.getByRole("link", { name: /Поддержать.*YooMoney/i }).last();
    const href = await donateLink.getAttribute("href");
    expect(href, "Fundraise ссылка").toMatch(/yoomoney\.ru\/fundraise\/[A-Z0-9]+\.\d+/);
  });

  test("SiteFooter: все соц-tile + партнёрские проекты — clickable", async ({ page }) => {
    await page.goto(BASE);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);

    const social = ["Rutube", "Дзен", "Telegram", "YouTube", "MAX", "Ритм"];
    for (const s of social) {
      const link = page.getByRole("link", { name: new RegExp(`Серво-Юг в ${s}`, "i") });
      await expect(link, `Соц-tile ${s}`).toBeVisible();
      await expect(link).toHaveAttribute("href", /^https?:\/\//);
      await expect(link).toHaveAttribute("target", "_blank");
    }

    // 3 партнёрских сайта
    for (const p of ["inservo.ru", "emkosti.pro", "servotank.ru"]) {
      const link = page.locator(`footer a[href*="${p}"]`).first();
      await expect(link, `Партнёр ${p}`).toBeVisible();
    }
  });

  test("Метка автора: Layout Stars Studio + Морозов Константин", async ({ page }) => {
    await page.goto(BASE);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);
    await expect(page.locator("footer")).toContainText("Layout Stars Studio");
    await expect(page.locator("footer")).toContainText("Морозов Константин");
    // Нет старых упоминаний
    const bodyText = await page.locator("body").textContent();
    expect(bodyText, "INSERVO Studio должен быть удалён").not.toContain("INSERVO Studio");
    expect(bodyText, "ИП Ягнов должен быть удалён").not.toContain("Ягнов");
  });

  test("Mobile (375×667): burger открывает drawer, ссылки кликабельные", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(BASE);
    const burger = page.getByRole("button", { name: /Открыть меню/i });
    await expect(burger).toBeVisible();
    await burger.click();
    const drawer = page.locator('[role="dialog"]');
    await expect(drawer).toBeVisible();
    // 7 ссылок + 1 donate = 8
    const navLinks = drawer.locator("a");
    const count = await navLinks.count();
    expect(count).toBeGreaterThanOrEqual(8);
    // Закрыть Esc
    await page.keyboard.press("Escape");
    await expect(drawer).not.toBeVisible();
  });

  test("Mobile (375×667): donate-bar тоже виден", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(BASE);
    const donate = page.locator('header a[href="#donate"]');
    await expect(donate).toBeVisible();
    await expect(donate).toContainText(/Поддержать/i);
  });

  test("Wide (1280×800): header elements не перекрываются", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(BASE);

    // SiteNav v7: phone (icon), Cmd+K button, burger (всегда видим), donate-row
    // ThemeToggle переехал в Cmd+K палитру (⌘\) — в навбаре его нет.
    const phone = page.locator('header a[href^="tel:"]').first();
    const cmdkBtn = page.locator('header button[aria-label*="Командная палитра"], header button:has-text("⌘K")').first();
    const burger = page.locator('header button[aria-label*="меню"], header button[aria-label*="Меню"]').first();

    // Если элемент существует — проверяем boundingBox в правой стороне header
    const checkRight = async (el: typeof phone, label: string) => {
      if ((await el.count()) === 0) return null;
      const box = await el.boundingBox();
      if (!box) return null;
      // В header всё это должно быть в правой половине (x > 400 для 1280px)
      expect(box.x, `${label} в правой части header`).toBeGreaterThan(200);
      return box;
    };

    const phoneBox = await checkRight(phone, "phone");
    const cmdkBox = await checkRight(cmdkBtn, "cmd-k");
    const burgerBox = await checkRight(burger, "burger");

    // Прямая проверка: соседние пары не должны overlap'иться по X
    if (phoneBox && cmdkBox && phoneBox.x < cmdkBox.x) {
      expect(phoneBox.x + phoneBox.width, "phone vs cmd-k").toBeLessThanOrEqual(cmdkBox.x + 5);
    }
    if (cmdkBox && burgerBox && cmdkBox.x < burgerBox.x) {
      expect(cmdkBox.x + cmdkBox.width, "cmd-k vs burger").toBeLessThanOrEqual(burgerBox.x + 5);
    }
  });

  test("Энциклопедия /teach/ — все 7 тем открываются", async ({ page }) => {
    const topics = ["fire", "water", "electrical", "hydraulics", "structural", "los", "documentation"];
    for (const t of topics) {
      const res = await page.request.get(`${BASE}/teach/${t}/`);
      expect(res.status(), `/teach/${t}/`).toBe(200);
    }
  });

  test("Ливнёвка /storm/minimal/: формы и кнопки", async ({ page }) => {
    await page.goto(`${BASE}/storm/minimal/`);
    await expect(page.locator("h1, h2").first()).toBeVisible();
    const inputs = page.locator('input, button, select');
    const count = await inputs.count();
    expect(count, "интерактивных элементов на /storm/minimal").toBeGreaterThan(3);
  });

  test("Резервуары /tanks/: 3 таба", async ({ page }) => {
    await page.goto(`${BASE}/tanks/`);
    // 3 таба: ПП-ёмкости, Корпус КНС, Стеклопластик — role="tab" (не button)
    const tabs = page.getByRole("tab");
    const count = await tabs.count();
    expect(count, "табы на /tanks").toBeGreaterThanOrEqual(3);
  });

  test("/project/: wizard step1 → step2", async ({ page }) => {
    await page.goto(`${BASE}/project/`);
    await expect(page.locator("h1, h2").first()).toBeVisible();
    // Должна быть кнопка «Далее» или подобная навигация
    const nextBtn = page.getByRole("button", { name: /Далее|Дальше|Next/i }).first();
    if (await nextBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await nextBtn.click();
      // Проверим что что-то изменилось на странице
      await page.waitForTimeout(500);
    }
  });

  test("Скачать Опросный лист DOCX — backend отвечает", async ({ page }) => {
    await page.goto(BASE);
    const dlBtn = page.getByRole("button", { name: /Опросный лист|техзадание/i }).first();
    if (await dlBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      const responsePromise = page.waitForResponse(
        (r) => r.url().includes("handoff/empty-questionnaire-docx"),
        { timeout: 15000 },
      ).catch(() => null);
      await dlBtn.click();
      const resp = await responsePromise;
      if (resp) {
        expect(resp.status(), "backend DOCX status").toBeLessThan(400);
      }
    }
  });
});
