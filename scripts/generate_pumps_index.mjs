#!/usr/bin/env node
// Генерирует lite-индекс насосов для Cmd+K палитры.
// Источник: 02_dataset/pumps/pumps.json (полные envelopes, ~800 KB).
// Цель: frontend/src/data/pumpsIndex.ts (~60-80 KB) — только поля,
// нужные для fuzzy-поиска и отображения в палитре.
//
// Запуск: `node scripts/generate_pumps_index.mjs` (через prebuild hook).

import { readFileSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const repoRoot = resolve(dirname(__filename), "..");

const pumpsPath = resolve(repoRoot, "02_dataset", "pumps", "pumps.json");
const indexPath = resolve(repoRoot, "frontend", "src", "data", "pumpsIndex.ts");

const raw = readFileSync(pumpsPath, "utf-8");
const data = JSON.parse(raw);

if (!Array.isArray(data.pumps)) {
  console.error("ERROR: pumps.json не содержит массива .pumps");
  process.exit(1);
}

const lite = data.pumps
  .map((p) => ({
    id: p.id,
    brand: p.brand,
    model: p.model,
    type: p.type,
    Q: p.envelope?.Q_BEP_m3h ?? null,
    H: p.envelope?.H_BEP_m ?? null,
    P: p.power?.P_kW ?? null,
    ex: !!p.power?.is_ex,
    segment: p.price_segment ?? null,
    price: p.price_rub_2026 ?? null,
  }))
  .filter((p) => p.id && p.brand && p.model)
  .sort((a, b) => {
    // Сортировка: сначала «budget» с реальной ценой (популярные бытовые),
    // затем остальные по brand+model.
    const aPop = a.segment === "budget" && a.price ? 0 : 1;
    const bPop = b.segment === "budget" && b.price ? 0 : 1;
    if (aPop !== bPop) return aPop - bPop;
    return `${a.brand} ${a.model}`.localeCompare(`${b.brand} ${b.model}`, "ru");
  });

const today = new Date().toISOString().slice(0, 10);

const content = `/**
 * Lite-индекс насосов для Cmd+K Command Palette.
 * Источник истины — 02_dataset/pumps/pumps.json.
 * Генерируется скриптом scripts/generate_pumps_index.mjs (prebuild hook).
 *
 * Поля: только то, что нужно для fuzzy-поиска и отображения карточки в палитре.
 * Размер: ~60-80 KB (вместо 800 KB полной БД).
 */
export interface PumpIndexItem {
  id: string;
  brand: string;
  model: string;
  type: string;
  Q: number | null;
  H: number | null;
  P: number | null;
  ex: boolean;
  segment: string | null;
  price: number | null;
}

export const PUMPS_INDEX_UPDATED_AT = "${today}";
export const PUMPS_INDEX: PumpIndexItem[] = ${JSON.stringify(lite, null, 0)};
`;

writeFileSync(indexPath, content, "utf-8");
const sizeKb = (Buffer.byteLength(content, "utf-8") / 1024).toFixed(1);
console.log(`OK: ${lite.length} pumps → ${indexPath} (${sizeKb} KB)`);
