import { z } from "zod";

/**
 * Зеркало backend/pump_calculator/schemas.py::L0Input.
 * При изменении backend — синхронизировать.
 */

export const wastewaterTypeSchema = z.enum(["domestic", "drainage", "industrial"]);
export type WastewaterType = z.infer<typeof wastewaterTypeSchema>;

export const wastewaterTypeLabels: Record<WastewaterType, string> = {
  domestic: "Хоз-бытовые",
  drainage: "Дренаж / ливнёвка",
  industrial: "Производственные",
};

export const qUnitSchema = z.enum(["m3h", "ls", "m3sut"]);
export type QUnit = z.infer<typeof qUnitSchema>;

export const qUnitLabels: Record<QUnit, string> = {
  m3h: "м³/ч",
  ls: "л/с",
  m3sut: "м³/сут",
};

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

/** L0Input — то что отправляем на backend. */
export const l0InputSchema = z.object({
  Q_m3h: z
    .number({ invalid_type_error: "Расход должен быть числом" })
    .positive("Расход должен быть больше 0")
    .max(10000, "Расход слишком большой (макс. 10 000 м³/ч)"),
  dH_m: z
    .number({ invalid_type_error: "Перепад должен быть числом" })
    .min(-50, "Перепад слишком отрицательный (мин. -50 м)")
    .max(200, "Перепад слишком большой (макс. 200 м)"),
  L_m: z
    .number({ invalid_type_error: "Длина должна быть числом" })
    .min(0, "Длина не может быть отрицательной")
    .max(5000, "Длина слишком большая (макс. 5000 м)"),
  wastewater_type: wastewaterTypeSchema,
});

export type L0Input = z.infer<typeof l0InputSchema>;

/** Форма пользователя — с unit и строковыми значениями полей до конвертации. */
export const wizardFormSchema = z.object({
  Q_value: z
    .union([z.string().min(1, "Введите расход"), z.number()])
    .pipe(z.coerce.number().positive("Расход должен быть больше 0")),
  Q_unit: qUnitSchema,
  dH_m: z
    .union([z.string().min(1, "Введите перепад точек"), z.number()])
    .pipe(z.coerce.number().min(-50).max(200)),
  L_m: z
    .union([z.string().min(0), z.number()])
    .pipe(z.coerce.number().min(0).max(5000)),
  wastewater_type: wastewaterTypeSchema,
});

export type WizardFormValues = z.infer<typeof wizardFormSchema>;

/** Преобразование формы в L0Input для отправки на backend. */
export function wizardFormToL0Input(form: WizardFormValues): L0Input {
  return {
    Q_m3h: toM3h(form.Q_value, form.Q_unit),
    dH_m: form.dH_m,
    L_m: form.L_m,
    wastewater_type: form.wastewater_type,
  };
}
