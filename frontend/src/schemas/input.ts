import { z } from "zod";

/**
 * Зеркало backend/pump_calculator/schemas.py::L0Input.
 * При изменении backend — синхронизировать.
 */

export const wastewaterTypeSchema = z.enum([
  "domestic",
  "drainage",
  "industrial",
  "clean_water",
]);
export type WastewaterType = z.infer<typeof wastewaterTypeSchema>;

export const wastewaterTypeLabels: Record<WastewaterType, string> = {
  domestic: "Бытовая канализация",
  drainage: "Дождевая / дренаж",
  industrial: "Промышленные стоки",
  clean_water: "Чистая вода (СПД)",
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

/** L0Input — то что отправляем на backend.
 * Только Q_m3h обязателен. Остальные поля опциональны: backend подставит дефолты
 * (см. apply_l0_defaults в matching.py) и вернёт их в `assumptions`.
 */
export const l0InputSchema = z.object({
  Q_m3h: z
    .number({ invalid_type_error: "Расход должен быть числом" })
    .positive("Расход должен быть больше 0")
    .max(10000, "Расход слишком большой (макс. 10 000 м³/ч)"),
  dH_m: z
    .number()
    .min(-50, "Перепад слишком отрицательный (мин. -50 м)")
    .max(200, "Перепад слишком большой (макс. 200 м)")
    .optional(),
  L_m: z
    .number()
    .min(0, "Длина не может быть отрицательной")
    .max(5000, "Длина слишком большая (макс. 5000 м)")
    .optional(),
  wastewater_type: wastewaterTypeSchema.optional(),
});

export type L0Input = z.infer<typeof l0InputSchema>;

/** Материал корпуса КНС (опциональный L1-параметр). */
export const corpusMaterialSchema = z.enum(["pe", "glass"]);
export type CorpusMaterial = z.infer<typeof corpusMaterialSchema>;

export const corpusMaterialLabels: Record<CorpusMaterial, string> = {
  pe: "Полиэтилен (ПЭ)",
  glass: "Стеклопластик",
};

/** L1Input — расширенные параметры. Сейчас на frontend используем только corpus_material;
 * остальные поля backend поддерживает но wizard их пока не предлагает.
 */
export const l1InputSchema = z.object({
  corpus_material: corpusMaterialSchema.optional(),
});

export type L1Input = z.infer<typeof l1InputSchema>;

/** Запрос на /select — обёртка с L0 и опциональным L1. */
export const selectionRequestSchema = z.object({
  L0: l0InputSchema,
  L1: l1InputSchema.optional(),
});

export type SelectionRequest = z.infer<typeof selectionRequestSchema>;

/** Форма пользователя — с unit; опциональные поля приходят пустыми строками. */
export const wizardFormSchema = z.object({
  Q_value: z
    .union([z.string().min(1, "Введите расход"), z.number()])
    .pipe(z.coerce.number().positive("Расход должен быть больше 0")),
  Q_unit: qUnitSchema,
  // Опциональные поля: пустая строка → undefined → backend подставит дефолт
  dH_m: z
    .union([z.string(), z.number()])
    .transform((v) => (v === "" || v === undefined ? undefined : Number(v)))
    .pipe(z.number().min(-50).max(200).optional()),
  L_m: z
    .union([z.string(), z.number()])
    .transform((v) => (v === "" || v === undefined ? undefined : Number(v)))
    .pipe(z.number().min(0).max(5000).optional()),
  wastewater_type: z.union([wastewaterTypeSchema, z.literal("")]).transform(
    (v): WastewaterType | undefined => (v === "" ? undefined : v),
  ),
  // L1 — материал корпуса (default "pe" чтобы radio было выбрано визуально)
  corpus_material: corpusMaterialSchema.default("pe"),
});

export type WizardFormValues = z.infer<typeof wizardFormSchema>;

/** Преобразование формы в SelectionRequest для отправки на backend.
 * Опциональные поля передаём только если заданы; иначе backend сам подставит дефолт.
 */
export function wizardFormToSelectionRequest(form: WizardFormValues): SelectionRequest {
  const L0: L0Input = {
    Q_m3h: toM3h(form.Q_value, form.Q_unit),
  };
  if (form.dH_m !== undefined) L0.dH_m = form.dH_m;
  if (form.L_m !== undefined) L0.L_m = form.L_m;
  if (form.wastewater_type !== undefined) L0.wastewater_type = form.wastewater_type;

  // L1 отправляем только если пользователь явно выбрал стеклопластик.
  // По умолчанию (pe) — не отправляем, backend применит default.
  const out: SelectionRequest = { L0 };
  if (form.corpus_material === "glass") {
    out.L1 = { corpus_material: "glass" };
  }
  return out;
}

/** Старая обёртка для backward-compat в существующих местах кода. */
export function wizardFormToL0Input(form: WizardFormValues): L0Input {
  return wizardFormToSelectionRequest(form).L0;
}
