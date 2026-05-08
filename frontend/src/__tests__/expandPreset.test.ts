// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
import { describe, it, expect } from "vitest";
import {
  expandPreset,
  getPreset,
  listPresets,
  m2ToHa,
  haToM2,
} from "@/lib/storm/expandPreset";

describe("expandPreset — Phase 19 Минимальный режим", () => {
  it("listPresets возвращает 7 пресетов MVP", () => {
    const presets = listPresets();
    expect(presets).toHaveLength(7);
    const ids = presets.map((p) => p.id);
    expect(ids).toContain("parking");
    expect(ids).toContain("roof");
    expect(ids).toContain("industrial");
  });

  it("getPreset парковки возвращает 100% asphalt", () => {
    const preset = getPreset("parking");
    expect(preset.surfaces.asphalt_share).toBe(1.0);
    expect(preset.t_concentration_min).toBe(10);
  });

  it("expandPreset для парковки 1 га → asphalt_ha=1.0", () => {
    const request = expandPreset({
      objectTypeId: "parking",
      area_ha: 1.0,
      region_city: "Краснодар",
    });
    expect(request.surfaces.asphalt_ha).toBeCloseTo(1.0);
    expect(request.surfaces.lawn_ha).toBe(0);
    expect(request.region_city).toBe("Краснодар");
    expect(request.sp_revision).toBe("SP_32_2018");
    expect(request.t_concentration_min).toBe(10);
  });

  it("expandPreset для коттеджного посёлка 2 га → правильное распределение", () => {
    const request = expandPreset({
      objectTypeId: "cottage_village",
      area_ha: 2.0,
      region_city: "Москва",
    });
    // 30% asphalt + 20% gravel + 50% lawn от 2 га
    expect(request.surfaces.asphalt_ha).toBeCloseTo(0.6);
    expect(request.surfaces.gravel_ha).toBeCloseTo(0.4);
    expect(request.surfaces.lawn_ha).toBeCloseTo(1.0);
  });

  it("expandPreset для промплощадки P=2 (СП 32 §6.6)", () => {
    const request = expandPreset({
      objectTypeId: "industrial",
      area_ha: 5.0,
      region_city: "Анапа",
    });
    expect(request.period_P_year).toBe(2);
    expect(request.t_concentration_min).toBe(15);
  });

  it("expandPreset для кровель — 100% roof", () => {
    const request = expandPreset({
      objectTypeId: "roof",
      area_ha: 0.5,
      region_city: "Сочи",
    });
    expect(request.surfaces.roof_ha).toBeCloseTo(0.5);
    expect(request.t_concentration_min).toBe(5); // кровельный сток быстрый
  });

  it("Сумма площадей в expandPreset равна area_ha", () => {
    const request = expandPreset({
      objectTypeId: "industrial",
      area_ha: 7.5,
      region_city: "Москва",
    });
    const total =
      request.surfaces.roof_ha +
      request.surfaces.asphalt_ha +
      request.surfaces.lawn_ha;
    expect(total).toBeCloseTo(7.5, 1);
  });

  it("getPreset бросает ошибку для несуществующего id", () => {
    expect(() =>
      // @ts-expect-error - intentionally invalid id
      getPreset("nonexistent_preset"),
    ).toThrow("Unknown object type");
  });
});

describe("Утилиты m2ToHa / haToM2", () => {
  it("m2ToHa: 10000 → 1", () => {
    expect(m2ToHa(10000)).toBe(1);
  });
  it("haToM2: 1 → 10000", () => {
    expect(haToM2(1)).toBe(10000);
  });
  it("Round-trip 5000 м² → га → м²", () => {
    expect(haToM2(m2ToHa(5000))).toBeCloseTo(5000);
  });
});
