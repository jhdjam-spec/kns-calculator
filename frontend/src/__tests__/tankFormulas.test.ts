import { describe, it, expect } from "vitest";
import {
  calcHorizontalTank,
  calcKnsCorpus,
  suggestKnsWallThickness,
  STANDARD_DIAMETERS_MM,
  SHEETS_PER_BAFFLE,
} from "@/lib/tankFormulas";

describe("calcHorizontalTank", () => {
  it("считает значения, сравнимые с ODS-калькулятором (D=3200, L=15000, t=12)", () => {
    // Это входные значения по умолчанию из ODS-файла Серво-Юг
    const result = calcHorizontalTank({
      L_mm: 15000,
      D_mm: 3200,
      t_corpus_mm: 12,
      t_baffle_mm: 12,
      t_band_mm: 8,
      baffle_step_m: 1.5,
      bands_per_section: 2,
      profiles_per_baffle: 4,
      profiles_longitudinal: 6,
      price_pp_kg: 240,
      price_profile_m: 1060,
    });

    // Объём ≈ 120.58 м³ в ODS (использует π=3.14), у нас Math.PI=3.14159 → 120.64
    // Разница ~0.06 м³ — ожидаемая, проверяем с точностью ±1 м³
    expect(result.V_m3).toBeCloseTo(120.6, 0);

    // Перегородок 11 (формула ceil(15000/1500)+1 = 11)
    expect(result.n_baffles).toBe(11);

    // Итого длина профилей ≈ 431.76 м в ODS (π=3.14), у нас 431.86 (Math.PI)
    expect(result.length_profiles_total_m).toBeCloseTo(431.8, 0);

    // Стоимость профилей ≈ 457 666 ± 200 (та же разница из-за π)
    expect(Math.abs(result.cost_profiles_rub - 457665.6)).toBeLessThan(200);
  });

  it("предупреждает о нестандартном диаметре", () => {
    const result = calcHorizontalTank({
      L_mm: 6000,
      D_mm: 1700, // нет в стандартном ряду
      t_corpus_mm: 10,
      t_baffle_mm: 10,
      t_band_mm: 8,
      baffle_step_m: 1.5,
      bands_per_section: 2,
      profiles_per_baffle: 4,
      profiles_longitudinal: 6,
      price_pp_kg: 240,
      price_profile_m: 1060,
    });
    expect(result.warnings.length).toBeGreaterThan(0);
    expect(result.warnings[0]).toMatch(/не из стандартного ряда/);
  });

  it("монотонность: увеличение L увеличивает массу и стоимость", () => {
    const base = {
      D_mm: 2400,
      t_corpus_mm: 10,
      t_baffle_mm: 10,
      t_band_mm: 8,
      baffle_step_m: 1.5,
      bands_per_section: 2,
      profiles_per_baffle: 4,
      profiles_longitudinal: 6,
      price_pp_kg: 240,
      price_profile_m: 1060,
    };
    const r1 = calcHorizontalTank({ ...base, L_mm: 6000 });
    const r2 = calcHorizontalTank({ ...base, L_mm: 12000 });
    expect(r2.mass_total_kg).toBeGreaterThan(r1.mass_total_kg);
    expect(r2.cost_total_rub).toBeGreaterThan(r1.cost_total_rub);
    expect(r2.V_m3).toBeCloseTo(r1.V_m3 * 2, 1);
  });
});

describe("SHEETS_PER_BAFFLE", () => {
  it("содержит все стандартные диаметры", () => {
    for (const d of STANDARD_DIAMETERS_MM) {
      expect(SHEETS_PER_BAFFLE[d]).toBeDefined();
    }
  });
});

describe("suggestKnsWallThickness", () => {
  it("для глубины 2 м рекомендует 8 мм", () => {
    expect(suggestKnsWallThickness(2000)).toBe(8);
  });
  it("для глубины 4 м рекомендует 12 мм", () => {
    expect(suggestKnsWallThickness(4000)).toBe(12);
  });
  it("для глубины 6 м рекомендует 20 мм", () => {
    expect(suggestKnsWallThickness(6000)).toBe(20);
  });
  it("для очень глубокого корпуса 8 м — макс. 20 мм", () => {
    expect(suggestKnsWallThickness(8000)).toBe(20);
  });
});

describe("calcKnsCorpus", () => {
  it("предупреждает при H/D > 4", () => {
    const result = calcKnsCorpus({
      D_mm: 1500,
      H_mm: 7000,
      t_wall_mm: 15,
      t_dome_mm: 15,
      price_pp_kg: 240,
    });
    expect(result.H_to_D).toBeCloseTo(4.67, 2);
    expect(result.warnings.some((w) => w.includes("H/D"))).toBe(true);
  });

  it("предупреждает о тонкой стенке для глубокого корпуса", () => {
    const result = calcKnsCorpus({
      D_mm: 2000,
      H_mm: 5000,
      t_wall_mm: 8,
      t_dome_mm: 12,
      price_pp_kg: 240,
    });
    expect(result.warnings.some((w) => w.includes("Толщина стенки"))).toBe(true);
  });

  it("без предупреждений для типового корпуса D1590 H3400 t12", () => {
    const result = calcKnsCorpus({
      D_mm: 1590,
      H_mm: 3400,
      t_wall_mm: 12,
      t_dome_mm: 12,
      price_pp_kg: 240,
    });
    expect(result.warnings).toHaveLength(0);
    expect(result.V_m3).toBeGreaterThan(6);
    expect(result.mass_total_kg).toBeGreaterThan(0);
  });
});
