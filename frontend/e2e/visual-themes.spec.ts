import { test } from "@playwright/test";
import * as path from "node:path";
import * as fs from "node:fs";

/**
 * Визуальный аудит: скриншоты ключевых страниц на live podborkns.ru
 * в light + dark темах. Фокус — проверка контраста SiteNav, drawer,
 * читаемости текста в обеих темах после фикса bg-ink-950 → bg-white dark:bg-ink-950.
 *
 * Сохраняет в test-results/visual-themes/<page>-<theme>.png
 */

const BASE = process.env.E2E_BASE_URL || "https://podborkns.ru";
const OUT_DIR = path.join(process.cwd(), "test-results", "visual-themes");
fs.mkdirSync(OUT_DIR, { recursive: true });

const PAGES: Array<{ slug: string; path: string }> = [
  { slug: "home", path: "/" },
  { slug: "teach-index", path: "/teach/" },
  { slug: "teach-hydraulics", path: "/teach/hydraulics/" },
  { slug: "tanks", path: "/tanks/" },
  { slug: "project", path: "/project/" },
  { slug: "storm", path: "/storm/minimal/" },
  { slug: "legal", path: "/legal/" },
];

const THEMES: Array<{ key: "light" | "dark" }> = [
  { key: "light" },
  { key: "dark" },
];

test.describe("Визуальный аудит: SiteNav + страницы в light/dark", () => {
  for (const page of PAGES) {
    for (const theme of THEMES) {
      test(`${page.slug} @ ${theme.key}`, async ({ page: pw }) => {
        // Установить тему ДО загрузки страницы — иначе FOUC
        await pw.addInitScript((t) => {
          try {
            localStorage.setItem("theme", t);
          } catch {
            /* noop */
          }
        }, theme.key);

        await pw.goto(`${BASE}${page.path}`, { waitUntil: "domcontentloaded" });
        await pw.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});

        // Скрин 1: вверху (видим navbar)
        const topShot = path.join(OUT_DIR, `${page.slug}-${theme.key}-top.png`);
        await pw
          .screenshot({ path: topShot, fullPage: false, timeout: 20_000 })
          .catch((e) =>
            test
              .info()
              .annotations.push({
                type: "screenshot-error",
                description: `${topShot}: ${(e as Error).message}`,
              }),
          );

        // Скрин 2: открытый burger drawer
        const burger = pw.locator('header button[aria-label*="меню"], header button[aria-label*="Меню"]').first();
        if ((await burger.count()) > 0) {
          await burger.click().catch(() => {});
          // Ждём пока React отрендерит nav-ссылки внутри drawer
          await pw
            .locator('div[role="dialog"][aria-label="Меню"] nav a')
            .first()
            .waitFor({ state: "visible", timeout: 5_000 })
            .catch(() => {});
          await pw.waitForTimeout(300);
          const drawerShot = path.join(OUT_DIR, `${page.slug}-${theme.key}-drawer.png`);
          await pw
            .screenshot({ path: drawerShot, fullPage: false, timeout: 20_000 })
            .catch(() => {});
        }
      });
    }
  }
});
