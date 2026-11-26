#!/usr/bin/env node
// Auto-генератор sitemap.xml + llms.txt-инвентаря для kns-calculator.
//
// Источник истины — этот скрипт: маршруты, приоритеты, частоты. Не редактируй
// сам frontend/public/sitemap.xml вручную, он будет перезаписан при следующем
// `npm run build` (через prebuild-хук).

import { writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const repoRoot = resolve(dirname(__filename), "..");
const publicDir = resolve(repoRoot, "frontend", "public");

// Production URL: https://podborkns.ru (с 2026-05-16).
// Старый: https://kns-calculator-frontend.website.yandexcloud.net
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://podborkns.ru";

const today = new Date().toISOString().slice(0, 10);

// Все публичные маршруты + приоритет (1.0 = главная) + changefreq.
// Если добавляется новая страница в src/app/, добавь её сюда.
const routes = [
  { path: "/", priority: 1.0, changefreq: "weekly" },
  { path: "/project", priority: 0.9, changefreq: "weekly" },
  { path: "/tanks", priority: 0.8, changefreq: "weekly" },
  { path: "/storm/minimal", priority: 0.8, changefreq: "weekly" },
  { path: "/import", priority: 0.7, changefreq: "weekly" },
  { path: "/teach", priority: 0.7, changefreq: "weekly" },
  { path: "/teach/fire", priority: 0.6, changefreq: "monthly" },
  { path: "/teach/water", priority: 0.6, changefreq: "monthly" },
  { path: "/teach/electrical", priority: 0.6, changefreq: "monthly" },
  { path: "/teach/hydraulics", priority: 0.6, changefreq: "monthly" },
  { path: "/teach/structural", priority: 0.6, changefreq: "monthly" },
  { path: "/teach/los", priority: 0.6, changefreq: "monthly" },
  { path: "/teach/documentation", priority: 0.6, changefreq: "monthly" },
  { path: "/teach/failure-modes", priority: 0.6, changefreq: "monthly" },
  { path: "/legal", priority: 0.3, changefreq: "yearly" },
];

const urlEntries = routes
  .map((r) => {
    return [
      "  <url>",
      `    <loc>${SITE_URL}${r.path}</loc>`,
      `    <lastmod>${today}</lastmod>`,
      `    <changefreq>${r.changefreq}</changefreq>`,
      `    <priority>${r.priority.toFixed(1)}</priority>`,
      "  </url>",
    ].join("\n");
  })
  .join("\n");

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urlEntries}
</urlset>
`;

const sitemapPath = resolve(publicDir, "sitemap.xml");
writeFileSync(sitemapPath, xml, "utf-8");
console.log(`OK: sitemap.xml (${routes.length} URLs) → ${sitemapPath}`);
