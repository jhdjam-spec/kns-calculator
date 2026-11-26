#!/usr/bin/env node
// Синхронизация PUMP_COUNT в frontend/src/data/pumpStats.ts со счётом
// в 02_dataset/pumps/pumps.json (поле `pumps`, массив объектов).
//
// Запуск: `node scripts/sync_pump_stats.mjs`
//
// Идея: счётчик «N моделей в базе» на главной (Hero + Trust компоненты)
// дрейфует относительно реальной БД, потому что обновлялся вручную и забывался.
// Теперь Hero/Trust читают PUMP_COUNT из shared-модуля, а этот скрипт держит
// его в синке с pumps.json. Можно повесить на pre-build хук (по желанию).

import { readFileSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const repoRoot = resolve(dirname(__filename), "..");

const pumpsPath = resolve(repoRoot, "02_dataset", "pumps", "pumps.json");
const statsPath = resolve(repoRoot, "frontend", "src", "data", "pumpStats.ts");

const raw = readFileSync(pumpsPath, "utf-8");
const data = JSON.parse(raw);

if (!Array.isArray(data.pumps)) {
  console.error("ERROR: pumps.json не содержит массива .pumps");
  process.exit(1);
}

const count = data.pumps.length;
const today = new Date().toISOString().slice(0, 10);

const content = `/**
 * Статистика по БД насосов. Источник истины — 02_dataset/pumps/pumps.json.
 * Обновляется автоматически скриптом \`scripts/sync_pump_stats.mjs\` перед билдом.
 *
 * Если число расходится с реальной БД, причиной обычно бывает забытый запуск
 * скрипта после правки pumps.json. Запустить: \`node scripts/sync_pump_stats.mjs\`.
 */
export const PUMP_COUNT = ${count};
export const PUMP_COUNT_UPDATED_AT = "${today}";
`;

writeFileSync(statsPath, content, "utf-8");
console.log(`OK: PUMP_COUNT=${count} → ${statsPath}`);
