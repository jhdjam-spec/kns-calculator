/**
 * Реализация модели горизонтальной ПП-ёмкости из 02_dataset/tanks/tank_calculator_models.json.
 * Источник формул: Калькулятор стоимости емкостей.ods (Серво-Юг).
 *
 * Все имена переменных совпадают с tank_calculator_models.json::horizontal_pp_tank.formulas
 * для трассируемости и поддержки.
 */

export const STANDARD_DIAMETERS_MM = [
  960, 1280, 1430, 1500, 1910, 2000, 2100, 2200, 2300, 2400, 2500, 3000, 3200, 3400, 3600,
] as const;

export const STANDARD_THICKNESSES_MM = [5, 6, 8, 10, 12, 15, 20] as const;

export const SHEETS_PER_BAFFLE: Record<number, number> = {
  960: 0.33, 1280: 0.5, 1430: 0.5, 1500: 0.5,
  1910: 1, 2000: 1, 2100: 1, 2200: 1,
  2300: 1.5, 2400: 1.5, 2500: 1.5,
  3000: 2, 3200: 2.3, 3400: 2.5, 3600: 2.6,
};

export const RHO_SHEET_KG_PER_MM = 4.14;
export const PROFILE_KG_PER_M = 3.6;
export const PP_OVERHEAD = 1.15;
export const PP_DOUBLING = 2;

export interface HorizontalTankInput {
  L_mm: number;
  D_mm: number;
  t_corpus_mm: number;
  t_baffle_mm: number;
  t_band_mm: number;
  baffle_step_m: number;
  bands_per_section: number;
  profiles_per_baffle: number;
  profiles_longitudinal: number;
  price_pp_kg: number;
  price_profile_m: number;
}

export interface HorizontalTankResult {
  V_m3: number;
  n_baffles: number;
  total_bands: number;
  length_bands_m: number;
  length_profiles_corpus_m: number;
  length_profiles_baffles_m: number;
  length_profiles_total_m: number;
  sheets_corpus: number;
  sheets_baffles: number;
  sheets_bands: number;
  mass_corpus_kg: number;
  mass_profiles_kg: number;
  mass_total_kg: number;
  cost_pp_rub: number;
  cost_profiles_rub: number;
  cost_total_rub: number;
  warnings: string[];
}

function ceilStep(value: number, step: number = 1): number {
  return Math.ceil(value / step) * step;
}

export function calcHorizontalTank(input: HorizontalTankInput): HorizontalTankResult {
  const {
    L_mm, D_mm, t_corpus_mm, t_baffle_mm, t_band_mm,
    baffle_step_m, bands_per_section, profiles_per_baffle, profiles_longitudinal,
    price_pp_kg, price_profile_m,
  } = input;

  const warnings: string[] = [];

  // Проверка дискретного D
  const sheets_per_baffle = SHEETS_PER_BAFFLE[D_mm];
  if (sheets_per_baffle === undefined) {
    warnings.push(
      `Диаметр ${D_mm} мм не из стандартного ряда — расчёт листов на перегородку приближённый. Рекомендуется выбрать из: ${STANDARD_DIAMETERS_MM.join(", ")}.`
    );
  }
  const sheets_per_baffle_safe = sheets_per_baffle ?? 1;

  // Геометрия
  const V_m3 = (Math.PI * (D_mm / 2) ** 2 * L_mm) / 1_000_000_000;
  const n_baffles = Math.ceil(L_mm / baffle_step_m / 1000) + 1;
  const total_bands = (n_baffles - 1) * bands_per_section;

  // Длины профилей
  const length_bands_m = (total_bands * Math.PI * D_mm) / 1000;
  const length_profiles_corpus_m = (profiles_longitudinal * L_mm) / 1000;
  const length_profiles_baffles_m = (n_baffles * D_mm * profiles_per_baffle) / 1000;
  const length_profiles_total_m =
    length_bands_m + length_profiles_corpus_m + length_profiles_baffles_m;

  // Площади листов (число стандартных листов 1500×3000)
  const sheets_corpus = ceilStep((L_mm / 1500) * (D_mm * Math.PI) / 3000, 0.5);
  const sheets_baffles = n_baffles * sheets_per_baffle_safe;
  const sheets_bands = ceilStep((length_bands_m / 100) * 11, 0.5);

  // Массы
  const mass_corpus_kg = RHO_SHEET_KG_PER_MM * (
    sheets_corpus * t_corpus_mm +
    sheets_baffles * t_baffle_mm +
    sheets_bands * t_band_mm
  );
  const mass_profiles_kg = length_profiles_total_m * PROFILE_KG_PER_M;
  const mass_total_kg = mass_corpus_kg + mass_profiles_kg;

  // Стоимость
  const cost_pp_rub = mass_corpus_kg * price_pp_kg * PP_OVERHEAD * PP_DOUBLING;
  const cost_profiles_rub = length_profiles_total_m * price_profile_m;
  const cost_total_rub = cost_pp_rub + cost_profiles_rub;

  return {
    V_m3, n_baffles, total_bands,
    length_bands_m, length_profiles_corpus_m, length_profiles_baffles_m, length_profiles_total_m,
    sheets_corpus, sheets_baffles, sheets_bands,
    mass_corpus_kg, mass_profiles_kg, mass_total_kg,
    cost_pp_rub, cost_profiles_rub, cost_total_rub,
    warnings,
  };
}

// ----------- KNS Vertical Corpus (упрощённая версия) -----------

export interface KnsCorpusInput {
  D_mm: number;        // диаметр КНС
  H_mm: number;        // высота корпуса
  t_wall_mm: number;   // толщина стенки
  t_dome_mm: number;   // толщина дна и крышки
  price_pp_kg: number;
}

export interface KnsCorpusResult {
  V_m3: number;
  H_to_D: number;
  sheets_wall: number;
  sheets_dome: number;
  mass_total_kg: number;
  cost_pp_rub: number;
  warnings: string[];
}

const T_MIN_BY_DEPTH = [
  { depth_max_m: 2.0, t_min_mm: 8 },
  { depth_max_m: 3.0, t_min_mm: 10 },
  { depth_max_m: 4.0, t_min_mm: 12 },
  { depth_max_m: 5.0, t_min_mm: 15 },
  { depth_max_m: 6.0, t_min_mm: 20 },
];

export function suggestKnsWallThickness(H_mm: number): number {
  const H_m = H_mm / 1000;
  for (const row of T_MIN_BY_DEPTH) {
    if (H_m <= row.depth_max_m) return row.t_min_mm;
  }
  return 20;
}

export function calcKnsCorpus(input: KnsCorpusInput): KnsCorpusResult {
  const { D_mm, H_mm, t_wall_mm, t_dome_mm, price_pp_kg } = input;
  const warnings: string[] = [];

  const V_m3 = (Math.PI * (D_mm / 2) ** 2 * H_mm) / 1_000_000_000;
  const H_to_D = H_mm / D_mm;

  if (H_to_D > 4) {
    warnings.push(
      `H/D = ${H_to_D.toFixed(1)} > 4. Слишком высокий корпус → проблемы с монтажом и обслуживанием (NOT_OK-22). Рекомендуемое H/D ≤ 3.`
    );
  }
  if (H_to_D < 1) {
    warnings.push(`H/D = ${H_to_D.toFixed(1)} < 1. Корпус слишком "сплюснут" — нерационально использует площадь.`);
  }

  const t_min = suggestKnsWallThickness(H_mm);
  if (t_wall_mm < t_min) {
    warnings.push(
      `Толщина стенки ${t_wall_mm} мм меньше рекомендованной (${t_min} мм для H = ${(H_mm / 1000).toFixed(1)} м). Возможна потеря прочности под грунтовым давлением.`
    );
  }

  // Стенка: цилиндрическая поверхность площадью π·D·H — переводим в стандартные листы 1500×3000
  const wall_area_m2 = (Math.PI * D_mm * H_mm) / 1_000_000;
  const sheets_wall = ceilStep(wall_area_m2 / 4.5, 0.5); // 1 лист = 4.5 м²

  // Дно + крышка: 2 круга диаметром D
  const dome_area_m2 = 2 * (Math.PI * (D_mm / 2) ** 2) / 1_000_000;
  const sheets_dome = ceilStep(dome_area_m2 / 4.5, 0.5);

  const mass_total_kg = RHO_SHEET_KG_PER_MM * (sheets_wall * t_wall_mm + sheets_dome * t_dome_mm);
  const cost_pp_rub = mass_total_kg * price_pp_kg * PP_OVERHEAD * PP_DOUBLING;

  return { V_m3, H_to_D, sheets_wall, sheets_dome, mass_total_kg, cost_pp_rub, warnings };
}
