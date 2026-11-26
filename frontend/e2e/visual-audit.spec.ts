import { test, expect, type Page, type ConsoleMessage } from "@playwright/test";
import fs from "fs";
import path from "path";

/**
 * Visual audit across all key pages of KNS Calculator.
 *
 * Iterates over routes × viewports (mobile / laptop), captures:
 *  - page errors (console.error + pageerror)
 *  - screenshots into `test-results/visual/<page>-<viewport>.png`
 *  - horizontal overflow on mobile (scrollWidth > viewport width)
 *  - "critical" element visibility (hero / main / footer)
 *
 * Also clicks main buttons on landing / project / storm / tanks / import.
 *
 * Run:
 *   E2E_BASE_URL=https://podborkns.ru npx playwright test e2e/visual-audit.spec.ts --workers=1
 */

type Route = { path: string; slug: string };

const ROUTES: Route[] = [
  { path: "/", slug: "home" },
  { path: "/project/", slug: "project" },
  { path: "/storm/minimal/", slug: "storm-minimal" },
  { path: "/tanks/", slug: "tanks" },
  { path: "/import/", slug: "import" },
  { path: "/teach/", slug: "teach" },
  { path: "/teach/fire/", slug: "teach-fire" },
  { path: "/teach/water/", slug: "teach-water" },
  { path: "/teach/electrical/", slug: "teach-electrical" },
  { path: "/teach/hydraulics/", slug: "teach-hydraulics" },
  { path: "/teach/structural/", slug: "teach-structural" },
  { path: "/teach/los/", slug: "teach-los" },
  { path: "/teach/documentation/", slug: "teach-documentation" },
  { path: "/teach/failure-modes/", slug: "teach-failure-modes" },
];

const VIEWPORTS = [
  { name: "mobile", width: 375, height: 667 },
  { name: "laptop", width: 1366, height: 800 },
];

const OUT_DIR = path.resolve(process.cwd(), "test-results/visual");
const REPORT_PATH = path.resolve(process.cwd(), "test-results/visual-audit.json");

type PageReport = {
  route: string;
  viewport: string;
  status: number | null;
  errors: string[];
  overflow: { scrollWidth: number; viewportWidth: number } | null;
  missingCritical: string[];
  clicks: Array<{ label: string; ok: boolean; error?: string }>;
  screenshot: string | null;
  loadError?: string;
};

const reports: PageReport[] = [];

test.beforeAll(() => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
});

function attachListeners(page: Page): { errors: string[] } {
  const errors: string[] = [];
  page.on("pageerror", (err) => {
    errors.push(`pageerror: ${err.message}`);
  });
  page.on("console", (msg: ConsoleMessage) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (
      text.includes("favicon") ||
      text.includes("Failed to load resource: net::ERR_") ||
      text.includes("React Query Devtools") ||
      text.includes("the server responded with a status of 404")
    ) {
      return;
    }
    errors.push(`console.error: ${text}`);
  });
  page.on("requestfailed", (req) => {
    const url = req.url();
    if (url.includes("favicon") || url.includes("data:image")) return;
    const failure = req.failure();
    if (failure && failure.errorText.includes("net::ERR_ABORTED")) return;
    errors.push(`requestfailed: ${req.method()} ${url} — ${failure?.errorText ?? "?"}`);
  });
  return { errors };
}

async function tryClick(
  page: Page,
  label: string,
  selector: () => Promise<boolean>,
): Promise<{ label: string; ok: boolean; error?: string }> {
  try {
    const ok = await selector();
    return { label, ok };
  } catch (err) {
    return { label, ok: false, error: (err as Error).message };
  }
}

async function exerciseHome(page: Page, clicks: PageReport["clicks"]) {
  // FAQ accordion
  clicks.push(
    await tryClick(page, "FAQ accordion", async () => {
      const summary = page.locator("summary, [aria-expanded]").first();
      if ((await summary.count()) === 0) return false;
      await summary.scrollIntoViewIfNeeded();
      await summary.click({ timeout: 3000 });
      return true;
    }),
  );

  // Hero submit (Q input + button)
  clicks.push(
    await tryClick(page, "Hero submit", async () => {
      const qInput = page.locator("#hero-q");
      if ((await qInput.count()) === 0) return false;
      await qInput.fill("12");
      const btn = page.getByRole("button", { name: /Рассчитать|Подобрать/i }).first();
      if ((await btn.count()) === 0) return false;
      await btn.click({ timeout: 4000 });
      return true;
    }),
  );

  // DonateCard input + Поддержать
  clicks.push(
    await tryClick(page, "Donate Поддержать", async () => {
      const donateInput = page.locator('input[type="number"][placeholder*="200"], input[id*="donate"]').first();
      if ((await donateInput.count()) > 0) {
        await donateInput.fill("300").catch(() => {});
      }
      const btn = page.getByRole("button", { name: /Поддержать/i }).first();
      const link = page.getByRole("link", { name: /Поддержать/i }).first();
      if ((await btn.count()) > 0) {
        await btn.scrollIntoViewIfNeeded();
        await btn.click({ timeout: 3000, trial: true });
        return true;
      }
      if ((await link.count()) > 0) {
        await link.scrollIntoViewIfNeeded();
        return true;
      }
      return false;
    }),
  );

  // Footer social tile
  clicks.push(
    await tryClick(page, "Footer social", async () => {
      const tile = page.locator("footer a[href*='t.me'], footer a[href*='wa.me'], footer a[href*='tel:']").first();
      if ((await tile.count()) === 0) return false;
      await tile.scrollIntoViewIfNeeded();
      return true;
    }),
  );
}

async function exerciseProject(page: Page, clicks: PageReport["clicks"]) {
  clicks.push(
    await tryClick(page, "Project: subsystem toggle", async () => {
      const toggles = page.locator("input[type='checkbox'], button[role='switch']");
      const cnt = await toggles.count();
      if (cnt === 0) return false;
      await toggles.first().click({ timeout: 3000, trial: true });
      return true;
    }),
  );

  clicks.push(
    await tryClick(page, "Project: Далее", async () => {
      const btn = page.getByRole("button", { name: /Далее/i }).first();
      if ((await btn.count()) === 0) return false;
      await btn.scrollIntoViewIfNeeded();
      await btn.click({ timeout: 3000, trial: true });
      return true;
    }),
  );

  clicks.push(
    await tryClick(page, "Project: Назад", async () => {
      const btn = page.getByRole("button", { name: /Назад/i }).first();
      if ((await btn.count()) === 0) return false;
      await btn.scrollIntoViewIfNeeded();
      await btn.click({ timeout: 3000, trial: true });
      return true;
    }),
  );
}

async function exerciseStorm(page: Page, clicks: PageReport["clicks"]) {
  clicks.push(
    await tryClick(page, "Storm: Рассчитать пиковый расход", async () => {
      const btn = page.getByRole("button", { name: /Рассчитать/i }).first();
      if ((await btn.count()) === 0) return false;
      await btn.scrollIntoViewIfNeeded();
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(800);
      return true;
    }),
  );
}

async function exerciseTanks(page: Page, clicks: PageReport["clicks"]) {
  for (const label of [/ПП/, /КНС/, /Стеклопл/]) {
    clicks.push(
      await tryClick(page, `Tanks tab ${label.source}`, async () => {
        const tab = page
          .locator(`button:has-text(${JSON.stringify(label.source)}), [role='tab']:has-text(${JSON.stringify(label.source)})`)
          .first();
        if ((await tab.count()) === 0) return false;
        await tab.scrollIntoViewIfNeeded();
        await tab.click({ timeout: 3000, trial: true });
        return true;
      }),
    );
  }
}

async function exerciseImport(page: Page, clicks: PageReport["clicks"]) {
  clicks.push(
    await tryClick(page, "Import: empty submit validation", async () => {
      const btn = page.getByRole("button", { name: /Импорт|Загрузить|Submit/i }).first();
      if ((await btn.count()) === 0) {
        // Try to find any submit button
        const anyBtn = page.locator("button[type='submit']").first();
        if ((await anyBtn.count()) === 0) return false;
        await anyBtn.click({ timeout: 3000, trial: true });
        return true;
      }
      await btn.scrollIntoViewIfNeeded();
      await btn.click({ timeout: 3000, trial: true });
      return true;
    }),
  );
}

for (const route of ROUTES) {
  for (const vp of VIEWPORTS) {
    test(`audit ${route.path} @ ${vp.name}`, async ({ browser }) => {
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        ignoreHTTPSErrors: true,
        locale: "ru-RU",
      });
      const page = await context.newPage();
      const { errors } = attachListeners(page);

      const report: PageReport = {
        route: route.path,
        viewport: vp.name,
        status: null,
        errors,
        overflow: null,
        missingCritical: [],
        clicks: [],
        screenshot: null,
      };

      try {
        const resp = await page.goto(route.path, { waitUntil: "domcontentloaded", timeout: 25_000 });
        report.status = resp?.status() ?? null;
        await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {});
        await page.waitForTimeout(500);

        // Overflow check
        const overflow = await page.evaluate(() => {
          const docW = document.documentElement.scrollWidth;
          const winW = window.innerWidth;
          return { scrollWidth: docW, viewportWidth: winW };
        });
        if (overflow.scrollWidth - overflow.viewportWidth > 2) {
          report.overflow = overflow;
        }

        // Critical elements
        const critical: Array<{ name: string; sel: string }> = [
          { name: "main landmark", sel: "main, [role='main']" },
          { name: "h1", sel: "h1" },
          { name: "footer", sel: "footer" },
        ];
        for (const c of critical) {
          const el = page.locator(c.sel).first();
          const count = await el.count();
          if (count === 0) {
            report.missingCritical.push(c.name);
            continue;
          }
          const visible = await el.isVisible().catch(() => false);
          if (!visible) report.missingCritical.push(`${c.name} (hidden)`);
        }

        // Exercise interactions
        if (route.path === "/" && vp.name === "laptop") {
          await exerciseHome(page, report.clicks);
        } else if (route.path === "/project/" && vp.name === "laptop") {
          await exerciseProject(page, report.clicks);
        } else if (route.path === "/storm/minimal/" && vp.name === "laptop") {
          await exerciseStorm(page, report.clicks);
        } else if (route.path === "/tanks/" && vp.name === "laptop") {
          await exerciseTanks(page, report.clicks);
        } else if (route.path === "/import/" && vp.name === "laptop") {
          await exerciseImport(page, report.clicks);
        }

        const shotPath = path.join(OUT_DIR, `${route.slug}-${vp.name}.png`);
        // Длинные markdown-страницы (/teach/*) fullPage может занимать >7s
        // (рендерим много контента, не critical для прохода теста)
        await page.screenshot({ path: shotPath, fullPage: true, timeout: 20_000 }).catch((e) => {
          report.loadError = `screenshot failed: ${(e as Error).message}`;
        });
        report.screenshot = path.relative(process.cwd(), shotPath);
      } catch (err) {
        report.loadError = (err as Error).message;
      } finally {
        reports.push(report);
        await context.close();
      }

      // Soft asserts: do not fail test — we want full audit run.
      expect(report.status === null || report.status < 400, `HTTP for ${route.path}: ${report.status}`).toBeTruthy();
    });
  }
}

test.afterAll(async () => {
  fs.writeFileSync(REPORT_PATH, JSON.stringify(reports, null, 2), "utf-8");

  // Human-readable summary to stdout
  const total = reports.length;
  const withErrors = reports.filter((r) => r.errors.length > 0);
  const withOverflow = reports.filter((r) => r.overflow !== null && r.viewport === "mobile");
  const withMissing = reports.filter((r) => r.missingCritical.length > 0);
  const failedClicks = reports.flatMap((r) => r.clicks.filter((c) => !c.ok).map((c) => ({ route: r.route, ...c })));
  const loadFails = reports.filter((r) => r.loadError);

  const lines: string[] = [];
  lines.push("\n========== VISUAL AUDIT SUMMARY ==========");
  lines.push(`Total runs: ${total} (routes × viewports)`);
  lines.push(`Runs with JS errors: ${withErrors.length}`);
  lines.push(`Runs with mobile overflow: ${withOverflow.length}`);
  lines.push(`Runs with missing critical elements: ${withMissing.length}`);
  lines.push(`Failed/missing clicks: ${failedClicks.length}`);
  lines.push(`Load failures: ${loadFails.length}`);

  if (loadFails.length) {
    lines.push("\n--- LOAD FAILURES ---");
    for (const r of loadFails) lines.push(`  ${r.route} @ ${r.viewport}: ${r.loadError}`);
  }
  if (withErrors.length) {
    lines.push("\n--- JS ERRORS ---");
    for (const r of withErrors) {
      lines.push(`  ${r.route} @ ${r.viewport}:`);
      for (const e of r.errors) lines.push(`    · ${e}`);
    }
  }
  if (withOverflow.length) {
    lines.push("\n--- MOBILE OVERFLOW ---");
    for (const r of withOverflow) {
      lines.push(`  ${r.route}: scrollWidth=${r.overflow!.scrollWidth}px > viewport=${r.overflow!.viewportWidth}px`);
    }
  }
  if (withMissing.length) {
    lines.push("\n--- MISSING CRITICAL ---");
    for (const r of withMissing) {
      lines.push(`  ${r.route} @ ${r.viewport}: ${r.missingCritical.join(", ")}`);
    }
  }
  if (failedClicks.length) {
    lines.push("\n--- FAILED CLICKS ---");
    for (const c of failedClicks) {
      lines.push(`  ${c.route} · ${c.label}: ${c.error ?? "not found"}`);
    }
  }
  lines.push(`\nFull JSON report: ${REPORT_PATH}`);
  lines.push("==========================================\n");
  // eslint-disable-next-line no-console
  console.log(lines.join("\n"));
});
