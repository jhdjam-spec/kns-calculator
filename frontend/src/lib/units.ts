import type { QUnit } from "@/schemas/input";

/** Конвертация в м³/ч (внутренний стандарт backend). */
export function toM3h(value: number, unit: QUnit): number {
  switch (unit) {
    case "m3h":
      return value;
    case "ls":
      return value * 3.6;
    case "m3sut":
      return value / 24;
  }
}

/** Конвертация из м³/ч в любую единицу — для отображения. */
export function fromM3h(m3h: number, unit: QUnit): number {
  switch (unit) {
    case "m3h":
      return m3h;
    case "ls":
      return m3h / 3.6;
    case "m3sut":
      return m3h * 24;
  }
}

/** Форматирование цены в рублях с разделителем тысяч и без копеек. */
export function formatRub(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(value >= 10_000_000 ? 0 : 1).replace(".", ",")} млн ₽`;
  }
  if (value >= 1000) {
    return `${Math.round(value / 1000)} ${value % 1000 === 0 ? "" : ""}тыс ₽`.trim();
  }
  return `${Math.round(value)} ₽`;
}

/** Полный формат с разделителем тысяч пробелом. */
export function formatRubFull(value: number): string {
  return `${Math.round(value).toLocaleString("ru-RU")} ₽`;
}

/** Расчёт match% между точкой работы и центром envelope насоса.
 * 100% — точное попадание в Q_BEP / H_BEP. Падает с расстоянием.
 */
export function calcMatchPct(
  Q_target: number,
  H_target: number,
  Q_BEP: number | null | undefined,
  H_BEP: number | null | undefined,
  envelope: { Q_min_m3h: number; Q_max_m3h: number; H_min_m: number; H_max_m: number },
): number {
  // Q-component: расстояние от Q_target до BEP, нормированное на ширину envelope
  const Q_center = Q_BEP ?? (envelope.Q_min_m3h + envelope.Q_max_m3h) / 2;
  const Q_width = Math.max(envelope.Q_max_m3h - envelope.Q_min_m3h, 1);
  const Q_dev = Math.abs(Q_target - Q_center) / Q_width;

  const H_center = H_BEP ?? (envelope.H_min_m + envelope.H_max_m) / 2;
  const H_width = Math.max(envelope.H_max_m - envelope.H_min_m, 1);
  const H_dev = Math.abs(H_target - H_center) / H_width;

  // Композит: 70% важности на Q, 30% на H
  const dev = 0.7 * Q_dev + 0.3 * H_dev;
  // 0 dev → 100%, 0.5 dev → 70%, 1+ → 50% min
  const score = Math.max(0.5, 1 - dev * 0.6);
  return Math.round(score * 100);
}
