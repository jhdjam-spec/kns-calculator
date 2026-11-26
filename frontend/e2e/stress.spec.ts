// ╭───────────────────────────────────────────────────────────────────────╮
// │ Stress-test podborkns.ru: 5 ключевых сценариев под нагрузкой.          │
// │ Цель — найти ошибки/timeouts/500-ки/UX-нестыковки.                     │
// │ Run: E2E_BASE_URL=https://podborkns.ru npx --no-install playwright    │
// │      test e2e/stress.spec.ts --workers=4 --reporter=line               │
// ╰───────────────────────────────────────────────────────────────────────╯
import { test, expect, type Page } from "@playwright/test";

const BASE = process.env.E2E_BASE_URL || "https://podborkns.ru";
const APIGW = "https://d5dnu7r53036cq815mes.ccx97b51.apigw.yandexcloud.net";

type Issue = { kind: string; detail: string; url?: string; status?: number };

function attachWatcher(page: Page): {
  errors: string[];
  failedRequests: Array<{ url: string; status: number }>;
} {
  const errors: string[] = [];
  const failedRequests: Array<{ url: string; status: number }> = [];
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => {
    if (m.type() !== "error") return;
    const txt = m.text();
    if (
      txt.includes("favicon") ||
      txt.includes("Failed to load resource: net::ERR_") ||
      txt.includes("React Query Devtools") ||
      txt.includes("yoomoney") // тосты внутри iframe yoomoney нас не касаются
    )
      return;
    errors.push(`console: ${txt}`);
  });
  page.on("response", (r) => {
    const status = r.status();
    const u = r.url();
    if (status >= 500 || (status >= 400 && /\/(select|storm|structural|project|handoff)/.test(u))) {
      // skip yoomoney noise
      if (u.includes("yoomoney.ru")) return;
      failedRequests.push({ url: u, status });
    }
  });
  return { errors, failedRequests };
}

// ─────────────────────────────────────────────────────────────────────
// Сценарий 1: Главная → подбор Q=21.2 → DOCX, ×10 параллельно
// ─────────────────────────────────────────────────────────────────────
test.describe("Сценарий 1: Home → select Q=21.2 (×10 параллельно)", () => {
  // Home loads with много JS, CTA+DOCX request — занимает 15-25s, в parallel ещё дольше.
  test.describe.configure({ timeout: 60_000 });

  for (let i = 0; i < 10; i++) {
    test(`run #${i + 1}: select + cards visible + DOCX 200`, async ({ page }) => {
      const w = attachWatcher(page);
      await page.goto(BASE, { waitUntil: "domcontentloaded" });

      const q = page.locator("#hero-q");
      await expect(q).toBeVisible({ timeout: 10_000 });
      await q.fill("21.2");

      // Wait backend response after click
      const respP = page
        .waitForResponse(
          (r) => /\/select\/quick|\/select(?:\?|$)/.test(r.url()),
          { timeout: 20_000 },
        )
        .catch(() => null);

      const cta = page
        .getByRole("button", { name: /Подобрать|Рассчитать/i })
        .first();
      await cta.click();

      const resp = await respP;
      if (resp) {
        expect(resp.status(), `select status (${resp.url()})`).toBeLessThan(500);
      }

      // Wait results section to mount
      await page.waitForTimeout(2500);
      // PumpCard или fallback section. Проверяем что цена/модель отрисовалась минимум 1.
      const cards = page.locator("[data-pump-card], [data-results], section");
      expect(await cards.count()).toBeGreaterThan(0);

      // Опросный лист DOCX
      const dlBtn = page
        .getByRole("button", { name: /Опросный лист|техзадание/i })
        .first();
      if (await dlBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        const docxResp = page
          .waitForResponse(
            (r) => r.url().includes("handoff/empty-questionnaire-docx"),
            { timeout: 15_000 },
          )
          .catch(() => null);
        await dlBtn.click();
        const dResp = await docxResp;
        if (dResp) {
          expect(dResp.status(), "DOCX endpoint status").toBeLessThan(400);
        }
      }

      expect(w.errors, `JS errors: ${w.errors.join("\n")}`).toEqual([]);
      expect(
        w.failedRequests,
        `Failed backend reqs: ${JSON.stringify(w.failedRequests)}`,
      ).toEqual([]);
    });
  }
});

// ─────────────────────────────────────────────────────────────────────
// Сценарий 2: Project Wizard полный цикл (×5)
// ─────────────────────────────────────────────────────────────────────
test.describe("Сценарий 2: Project Wizard hotel (×5)", () => {
  // Wizard состоит из 4 шагов; preset-кнопки кликаются 1 раз и auto-advance не работает.
  // Используем длинный timeout, тк ProjectStepResults рендерит много текста + 3 subsystem-расчёта.
  test.describe.configure({ timeout: 90_000 });

  for (let i = 0; i < 5; i++) {
    test(`run #${i + 1}: preset → params → subsystems → results`, async ({
      page,
    }) => {
      const w = attachWatcher(page);
      await page.goto(`${BASE}/project/`, { waitUntil: "domcontentloaded" });
      await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});

      // Step 1: «Гостиница / отель» — preset карточка
      const hotelBtn = page
        .getByRole("button", { name: /Гостиница/i })
        .first();
      await expect(hotelBtn, "preset hotel button").toBeVisible({ timeout: 10_000 });
      await hotelBtn.click();
      await page.waitForTimeout(300);

      // «Далее» → params
      const next1 = page.getByRole("button", { name: /^Далее|Дальше|Next/i }).first();
      if (await next1.isVisible({ timeout: 3000 }).catch(() => false)) {
        await next1.click();
      }

      // Step 2: params (population 120, volume 8000, Q 26)
      await page.waitForTimeout(500);
      // На params: заполняем все числовые поля поочерёдно.
      const allNum = page.locator('input[type="number"]');
      const cnt = await allNum.count();
      // По коду ProjectWizard: data already has population, floors, volume_m3, area_m2.
      // Заполним 3 первых — этого достаточно для backend.
      if (cnt >= 1) await allNum.nth(0).fill("120");
      if (cnt >= 2) await allNum.nth(1).fill("8000");
      if (cnt >= 3) await allNum.nth(2).fill("4");

      const next2 = page.getByRole("button", { name: /^Далее|Дальше/i }).first();
      if (await next2.isVisible({ timeout: 3000 }).catch(() => false)) {
        await next2.click();
      }

      // Step 3: subsystems — кнопки-чипы (button с ✓/✗). Уже преселектированы пресетом.
      await page.waitForTimeout(500);
      // Рассчитать — текст кнопки в ProjectStepSubsystems: «Рассчитать» / «Считаем…»
      const respP = page
        .waitForResponse((r) => /\/project\/calculate/.test(r.url()), {
          timeout: 30_000,
        })
        .catch(() => null);
      const calcBtn = page
        .getByRole("button", { name: /Рассчитать проект|Рассчитать$|Расчёт|Готово/i })
        .first();
      await expect(calcBtn, "Calc button").toBeVisible({ timeout: 5000 });
      await calcBtn.click();

      const resp = await respP;
      if (resp) {
        expect(resp.status(), `/project/calculate status`).toBeLessThan(500);
      }

      // Step 4: results — BOM или сводка
      await page.waitForTimeout(2000);
      const bodyText = await page.locator("body").textContent();
      expect(bodyText?.length ?? 0).toBeGreaterThan(200);
      // На странице результатов должна быть сводка по подсистемам или BOM
      expect(bodyText, "должен быть результат расчёта").toMatch(/КНС|ВНС|спецификац|итог|стоимост|насос/i);

      expect(w.errors, `JS: ${w.errors.join("\n")}`).toEqual([]);
      const fatal = w.failedRequests.filter((r) => r.status >= 500);
      expect(fatal, `5xx errors: ${JSON.stringify(fatal)}`).toEqual([]);
    });
  }
});

// ─────────────────────────────────────────────────────────────────────
// Сценарий 3: Storm minimal × 5
// ─────────────────────────────────────────────────────────────────────
test.describe("Сценарий 3: Storm minimal (×5)", () => {
  for (let i = 0; i < 5; i++) {
    test(`run #${i + 1}: roof + 5000 m² Москва → submit enable + расчёт`, async ({
      page,
    }) => {
      const w = attachWatcher(page);
      await page.goto(`${BASE}/storm/minimal/`, { waitUntil: "domcontentloaded" });
      await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});

      // 1. Выбрать «Кровли»
      const roof = page
        .getByRole("button", { name: /кровл|крыш|roof/i })
        .first();
      await expect(roof, "Кнопка «Кровли» должна найтись").toBeVisible({
        timeout: 5000,
      });
      await roof.click();

      // 2. Площадь 5000 м²
      const areaInput = page
        .locator('input[type="number"], input[inputmode="decimal"], input[inputmode="numeric"]')
        .first();
      await areaInput.fill("5000");

      // 3. Город: печатаем «Москва», blur
      const cityInput = page
        .locator('input[type="text"][placeholder*="печатат"]')
        .first();
      await expect(cityInput).toBeVisible({ timeout: 5000 });
      await cityInput.fill("Москва");
      // blur → должно сработать автоподтверждение
      await cityInput.blur();
      await page.waitForTimeout(500);

      // 4. Submit должна стать enabled
      const submit = page
        .getByRole("button", { name: /Рассчитать пиковый|пиковый расход|Рассчитать/i })
        .first();
      await expect(
        submit,
        "Submit должна enable'иться после blur по городу",
      ).toBeEnabled({ timeout: 5000 });

      // 5. Расчёт
      const respP = page
        .waitForResponse((r) => /\/storm\/calc/.test(r.url()), { timeout: 20_000 })
        .catch(() => null);
      await submit.click();
      const resp = await respP;
      if (resp) {
        expect(resp.status(), `/storm/calc status`).toBeLessThan(400);
      }
      await page.waitForTimeout(2000);
      // Результат должен показать Q (л/с) хоть где-то
      const body = await page.locator("body").textContent();
      expect(body, "должно быть упоминание л/с в результате").toMatch(/л\/с|l\/s/i);

      expect(w.errors, `JS: ${w.errors.join("\n")}`).toEqual([]);
      const fatal = w.failedRequests.filter((r) => r.status >= 500);
      expect(fatal, `5xx errors: ${JSON.stringify(fatal)}`).toEqual([]);
    });
  }
});

// ─────────────────────────────────────────────────────────────────────
// Сценарий 4: /tanks/ → КНС → прочностной чек (новая фича)
// ─────────────────────────────────────────────────────────────────────
test.describe("Сценарий 4: tanks → КНС → прочностной чек", () => {
  test("раскрытие секции + 2 карточки (Толщина + Пригруз)", async ({ page }) => {
    const w = attachWatcher(page);
    await page.goto(`${BASE}/tanks/`, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});

    // Переключиться на «Корпус КНС» (2й таб). На моб. subtitle скрыт, но текст «Корпус КНС» есть всегда.
    const knsTab = page
      .locator('[role="tab"]')
      .filter({ hasText: /Корпус КНС/i })
      .first();
    await expect(knsTab).toBeVisible({ timeout: 5000 });
    await knsTab.click();
    await page.waitForTimeout(500);

    // Раскрыть «Проверить прочность корпуса»
    const expander = page
      .getByRole("button", { name: /проверить прочность корпуса/i })
      .first();
    await expect(expander).toBeVisible({ timeout: 5000 });
    await expander.click();
    await page.waitForTimeout(300);

    // Заполнить поля
    const panel = page.locator("#strength-panel");
    await expect(panel).toBeVisible();
    const numericInputs = panel.locator('input[type="number"]');
    const ic = await numericInputs.count();
    if (ic >= 1) await numericInputs.nth(0).fill("3.4"); // глубина
    if (ic >= 2) await numericInputs.nth(1).fill("0.5"); // УГВ
    if (ic >= 3) await numericInputs.nth(2).fill("20"); // заполнение

    // Грунт: суглинок
    const select = panel.locator("select");
    if ((await select.count()) > 0) {
      await select.selectOption("loam").catch(() => {});
    }

    // Запустить проверку
    const run = panel
      .getByRole("button", { name: /Запустить проверку|Считаем/i })
      .first();
    const respBallast = page
      .waitForResponse((r) => r.url().includes("/structural/ballast"), {
        timeout: 15_000,
      })
      .catch(() => null);
    const respWall = page
      .waitForResponse((r) => r.url().includes("/structural/wall-thickness"), {
        timeout: 15_000,
      })
      .catch(() => null);
    await run.click();
    const [b, wResp] = await Promise.all([respBallast, respWall]);
    if (b) expect(b.status(), `ballast status`).toBeLessThan(400);
    if (wResp) expect(wResp.status(), `wall-thickness status`).toBeLessThan(400);

    // Ждём отрисовку карточек
    await page.waitForTimeout(1500);
    const body = await panel.textContent();
    expect(body, "должна быть карточка «Толщина»").toMatch(/Толщина стенки/i);
    expect(body, "должна быть карточка «Пригруз»").toMatch(/пригруз/i);
    // Числовые значения видимы (кН и/или мм)
    expect(body).toMatch(/кН|кн|мм/i);

    expect(w.errors, `JS: ${w.errors.join("\n")}`).toEqual([]);
  });
});

// ─────────────────────────────────────────────────────────────────────
// Сценарий 5: DonateCard
// ─────────────────────────────────────────────────────────────────────
test.describe("Сценарий 5: DonateCard fundraise", () => {
  test("iframe yoomoney + кнопка ведёт на /fundraise/<billNumber>", async ({
    page,
  }) => {
    const w = attachWatcher(page);

    let iframeStatus: number | null = null;
    page.on("response", (r) => {
      if (r.url().includes("yoomoney.ru/quickpay/fundraise/widget")) {
        iframeStatus = r.status();
      }
    });

    await page.goto(BASE, { waitUntil: "domcontentloaded" });
    // home большая — ждём пока DonateCard смонтируется. Scroll к секции donate.
    await page.waitForLoadState("networkidle", { timeout: 20_000 }).catch(() => {});
    await page.locator("#donate").scrollIntoViewIfNeeded({ timeout: 10_000 }).catch(() => {});
    await page.waitForTimeout(2000); // дать iframe загрузиться (lazy)

    // iframe present
    const iframe = page.locator('iframe[src*="yoomoney.ru/quickpay/fundraise/widget"]');
    await expect(iframe, "Виджет YooMoney должен присутствовать").toHaveCount(1, { timeout: 10_000 });
    const src = await iframe.getAttribute("src");
    expect(src).toContain("1HQ93GCV7OQ.260517");

    // Кнопка ведёт на /fundraise/<id>. aria-label = "Перейти на страницу сбора YooMoney"
    const link = page
      .locator('a[href*="yoomoney.ru/fundraise/"]')
      .first();
    await expect(link).toBeVisible({ timeout: 10_000 });
    const href = await link.getAttribute("href");
    expect(href, "Поддержать ссылка").toMatch(
      /yoomoney\.ru\/fundraise\/1HQ93GCV7OQ\.260517/,
    );

    // iframe вернул 200 (или null если он lazy и не загрузился — допустимо)
    const status = iframeStatus as number | null;
    if (status !== null) {
      expect(status, "yoomoney widget status").toBeLessThan(400);
    }

    // JS-ошибки в нашем коде
    expect(w.errors, `JS: ${w.errors.join("\n")}`).toEqual([]);
  });
});

// ─────────────────────────────────────────────────────────────────────
// MOBILE 375px — все 5 сценариев лайт-вариант
// ─────────────────────────────────────────────────────────────────────
test.describe("Mobile 375px: все 5 сценариев", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("Сц.1 mobile: Q=21.2 → подбор", async ({ page }) => {
    const w = attachWatcher(page);
    await page.goto(BASE, { waitUntil: "domcontentloaded" });
    const q = page.locator("#hero-q");
    await expect(q).toBeVisible({ timeout: 10_000 });
    await q.fill("21.2");
    const respP = page
      .waitForResponse((r) => /\/select\/quick/.test(r.url()), { timeout: 20_000 })
      .catch(() => null);
    await page
      .getByRole("button", { name: /Подобрать|Рассчитать/i })
      .first()
      .click();
    const resp = await respP;
    if (resp) expect(resp.status()).toBeLessThan(500);
    await page.waitForTimeout(2000);
    expect(w.errors, w.errors.join("\n")).toEqual([]);
  });

  test("Сц.2 mobile: /project/ открывается, wizard шаги видны", async ({ page }) => {
    const w = attachWatcher(page);
    await page.goto(`${BASE}/project/`, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});
    const heading = page.locator("h1, h2").first();
    await expect(heading).toBeVisible();
    expect(w.errors, w.errors.join("\n")).toEqual([]);
  });

  test("Сц.3 mobile: storm minimal — submit включается после blur", async ({
    page,
  }) => {
    const w = attachWatcher(page);
    await page.goto(`${BASE}/storm/minimal/`, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});
    const roof = page.getByRole("button", { name: /кровл/i }).first();
    await expect(roof).toBeVisible({ timeout: 5000 });
    await roof.click();
    // AreaInput использует type="text" inputMode="decimal", не type="number"!
    const area = page.locator('input[inputmode="decimal"]').first();
    await expect(area).toBeVisible({ timeout: 5000 });
    await area.fill("5000");
    const city = page.locator('input[placeholder*="печатат"]').first();
    await city.fill("Москва");
    await city.blur();
    await page.waitForTimeout(500);
    const submit = page.getByRole("button", { name: /Рассчитать/i }).first();
    await expect(submit).toBeEnabled({ timeout: 5000 });
    expect(w.errors, w.errors.join("\n")).toEqual([]);
  });

  test("Сц.4 mobile: tanks → КНС → прочностной чек открывается", async ({ page }) => {
    const w = attachWatcher(page);
    await page.goto(`${BASE}/tanks/`, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});
    const knsTab = page
      .locator('[role="tab"]')
      .filter({ hasText: /Корпус КНС/i })
      .first();
    await expect(knsTab).toBeVisible({ timeout: 5000 });
    await knsTab.click();
    const expander = page
      .getByRole("button", { name: /проверить прочность корпуса/i })
      .first();
    await expect(expander).toBeVisible({ timeout: 5000 });
    await expander.click();
    await expect(page.locator("#strength-panel")).toBeVisible();
    expect(w.errors, w.errors.join("\n")).toEqual([]);
  });

  test("Сц.5 mobile: donate iframe и кнопка видны", async ({ page }) => {
    const w = attachWatcher(page);
    await page.goto(BASE, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 20_000 }).catch(() => {});
    await page.locator("#donate").scrollIntoViewIfNeeded({ timeout: 10_000 }).catch(() => {});
    await page.waitForTimeout(2000);
    const link = page.locator('a[href*="yoomoney.ru/fundraise/"]').first();
    await expect(link).toBeVisible({ timeout: 10_000 });
    const iframe = page.locator(
      'iframe[src*="yoomoney.ru/quickpay/fundraise/widget"]',
    );
    await expect(iframe).toHaveCount(1, { timeout: 10_000 });
    expect(w.errors, w.errors.join("\n")).toEqual([]);
  });
});
