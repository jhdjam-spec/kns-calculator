import { describe, it, expect } from "vitest";
import {
  l0InputSchema,
  toM3h,
  wizardFormSchema,
  wizardFormToL0Input,
} from "@/schemas/input";

describe("toM3h conversion", () => {
  it("конвертирует м³/ч в м³/ч без изменений", () => {
    expect(toM3h(21.2, "m3h")).toBe(21.2);
  });

  it("конвертирует л/с в м³/ч (×3.6)", () => {
    expect(toM3h(5.9, "ls")).toBeCloseTo(21.24, 2);
  });

  it("конвертирует м³/сут в м³/ч (÷24)", () => {
    expect(toM3h(48, "m3sut")).toBe(2);
  });
});

describe("l0InputSchema", () => {
  it("принимает корректные данные", () => {
    const ok = l0InputSchema.safeParse({
      Q_m3h: 21.2,
      dH_m: 10,
      L_m: 0,
      wastewater_type: "domestic",
    });
    expect(ok.success).toBe(true);
  });

  it("отвергает Q ≤ 0", () => {
    const r = l0InputSchema.safeParse({
      Q_m3h: 0,
      dH_m: 10,
      L_m: 0,
      wastewater_type: "domestic",
    });
    expect(r.success).toBe(false);
  });

  it("отвергает Q > 10000", () => {
    const r = l0InputSchema.safeParse({
      Q_m3h: 50000,
      dH_m: 10,
      L_m: 0,
      wastewater_type: "domestic",
    });
    expect(r.success).toBe(false);
  });

  it("отвергает невалидный wastewater_type", () => {
    const r = l0InputSchema.safeParse({
      Q_m3h: 10,
      dH_m: 10,
      L_m: 0,
      wastewater_type: "invalid",
    });
    expect(r.success).toBe(false);
  });

  it("отвергает L_m отрицательный", () => {
    const r = l0InputSchema.safeParse({
      Q_m3h: 10,
      dH_m: 10,
      L_m: -5,
      wastewater_type: "domestic",
    });
    expect(r.success).toBe(false);
  });
});

describe("wizardFormSchema (со строковым вводом)", () => {
  it("парсит строки в числа через z.coerce", () => {
    const r = wizardFormSchema.safeParse({
      Q_value: "21.2",
      Q_unit: "m3h",
      dH_m: "10",
      L_m: "0",
      wastewater_type: "domestic",
    });
    expect(r.success).toBe(true);
    if (r.success) {
      expect(r.data.Q_value).toBe(21.2);
      expect(r.data.dH_m).toBe(10);
    }
  });
});

describe("wizardFormToL0Input", () => {
  it("конвертирует форму с л/с в м³/ч для L0Input", () => {
    const result = wizardFormToL0Input({
      Q_value: 5.9,
      Q_unit: "ls",
      dH_m: 10,
      L_m: 0,
      wastewater_type: "domestic",
    });
    expect(result.Q_m3h).toBeCloseTo(21.24, 2);
    expect(result.wastewater_type).toBe("domestic");
  });
});

describe("L0Input — опциональные поля (Phase 6+)", () => {
  it("принимает только Q_m3h без остальных полей", () => {
    const ok = l0InputSchema.safeParse({ Q_m3h: 21.2 });
    expect(ok.success).toBe(true);
  });

  it("wizardFormToL0Input не отправляет undefined-поля", () => {
    const result = wizardFormToL0Input({
      Q_value: 21.2,
      Q_unit: "m3h",
      dH_m: undefined,
      L_m: undefined,
      wastewater_type: undefined,
    });
    expect(result.Q_m3h).toBe(21.2);
    expect("dH_m" in result).toBe(false);
    expect("L_m" in result).toBe(false);
    expect("wastewater_type" in result).toBe(false);
  });

  it("wizardFormSchema преобразует пустую строку в undefined", () => {
    const r = wizardFormSchema.safeParse({
      Q_value: "21.2",
      Q_unit: "m3h",
      dH_m: "",
      L_m: "",
      wastewater_type: "",
    });
    expect(r.success).toBe(true);
    if (r.success) {
      expect(r.data.dH_m).toBeUndefined();
      expect(r.data.L_m).toBeUndefined();
      expect(r.data.wastewater_type).toBeUndefined();
    }
  });
});
