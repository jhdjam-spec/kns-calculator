/**
 * Статистика по БД насосов. Источник истины — 02_dataset/pumps/pumps.json.
 * Обновляется автоматически скриптом `scripts/sync_pump_stats.mjs` перед билдом.
 *
 * Если число расходится с реальной БД, причиной обычно бывает забытый запуск
 * скрипта после правки pumps.json. Запустить: `node scripts/sync_pump_stats.mjs`.
 */
export const PUMP_COUNT = 494;
export const PUMP_COUNT_UPDATED_AT = "2026-11-14";
