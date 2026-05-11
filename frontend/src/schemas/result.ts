import { z } from "zod";

/**
 * Зеркало backend/pump_calculator/schemas.py::SelectionResult.
 * Используем z.unknown() / z.record() для полей которые нам сейчас не нужны типизировать строго,
 * чтобы не дублировать всю Pydantic-схему — нам нужен только display.
 */

export const pumpEnvelopeSchema = z.object({
  Q_min_m3h: z.number(),
  Q_max_m3h: z.number(),
  H_min_m: z.number(),
  H_max_m: z.number(),
  Q_BEP_m3h: z.number().nullable().optional(),
  H_BEP_m: z.number().nullable().optional(),
  eta_BEP_pct: z.number().nullable().optional(),
  NPSHr_at_BEP_m: z.number().nullable().optional(),
});

export const priceBreakdownSchema = z.object({
  pump_rub: z.number().default(0),
  atm_rub: z.number().default(0),
  valve_rub: z.number().default(0),
  check_valve_rub: z.number().default(0),
  rails_rub: z.number().default(0),
  cabinet_rub: z.number().default(0),
  floats_rub: z.number().default(0),
  chain_rub: z.number().default(0),
  corpus_rub: z.number().default(0),
  total_rub: z.number().default(0),
  // Phase 9: диапазон цены (зависит от полноты ввода)
  total_low_rub: z.number().default(0),
  total_high_rub: z.number().default(0),
});

export type PriceBreakdown = z.infer<typeof priceBreakdownSchema>;

export const pumpResultSchema = z.object({
  id: z.string(),
  brand: z.string(),
  model: z.string(),
  type: z.string(),
  impeller: z.string().nullable().optional(),
  free_passage_mm: z.number(),
  envelope: pumpEnvelopeSchema,
  P_kW: z.number(),
  discharge_DN_mm: z.number().nullable().optional(),
  price_segment: z.enum(["budget", "mid", "premium"]),
  available_ru_status: z.string(),
  score: z.number(),
  score_breakdown: z.record(z.number()).default({}),
  // 2026-05-11 «Why this pump?» — пошаговое объяснение подбора для UI explainer
  // (см. backend/pump_calculator/matching.py::build_score_explanation).
  // Структура свободная (passthrough) — UI читает поля step_1_filter,
  // step_2_envelope, step_3_aor, step_4_composite (dict factor → {value,
  // weight, contribution, label, hint_engineer, hint_manager}),
  // step_5_segment, rank_in_segment, candidates_in_segment, citations[].
  score_explanation: z.record(z.unknown()).optional().default({}),
  duty_point: z.record(z.number()).nullable().optional(),
  aor_zone: z.enum(["POR", "AOR", "outside"]).nullable().optional(),
  notes: z.array(z.string()).default([]),
  // Phase 6+ — первичная оценка цены КНС-комплекта
  price_estimate_rub: z.number().default(0),
  price_breakdown: priceBreakdownSchema.default({
    pump_rub: 0, atm_rub: 0, valve_rub: 0, check_valve_rub: 0,
    rails_rub: 0, cabinet_rub: 0, floats_rub: 0, chain_rub: 0,
    corpus_rub: 0, total_rub: 0,
  }),
  price_confidence: z.enum(["low", "medium", "high"]).default("low"),
});

export type PumpResult = z.infer<typeof pumpResultSchema>;

export const computedHydraulicsSchema = z.object({
  D_mm: z.number(),
  v_ms: z.number(),
  Re: z.number(),
  friction_factor: z.number(),
  H_tr_m: z.number(),
  sum_zeta: z.number(),
  H_m_m: z.number(),
  H_full_m: z.number(),
  safety_factor: z.number(),
});

export type ComputedHydraulics = z.infer<typeof computedHydraulicsSchema>;

/**
 * Зеркало backend `InputSuggestion` (commit afcea84 / 2beab6a).
 * Backend советует поправить ввод когда видит подозрительные значения.
 * - reason — старое поле, оставляем для backward compat.
 * - reason_engineer/reason_manager — расширенные тексты (2beab6a) для tab toggle.
 */
export const inputSuggestionSchema = z.object({
  field: z.string(),
  current_value: z.string(),
  suggested_value: z.string(),
  reason: z.string().default(""),
  reason_engineer: z.string().optional(),
  reason_manager: z.string().optional(),
  severity: z.enum(["info", "warning", "critical"]).default("info"),
});

export type InputSuggestion = z.infer<typeof inputSuggestionSchema>;

export const selectionResultSchema = z.object({
  schema_version: z.string(),
  input: z.unknown(), // не парсим строго — это копия input
  computed: computedHydraulicsSchema,
  results: z.object({
    budget: pumpResultSchema.nullable(),
    mid: pumpResultSchema.nullable(),
    premium: pumpResultSchema.nullable(),
  }),
  candidates_total: z.number(),
  warnings: z.array(z.string()),
  engineer_handoff_required: z.boolean(),
  trigger_reasons: z.array(z.string()),
  // Phase 6+ — список дефолтов, подставленных при неполном L0
  assumptions: z.array(z.string()).default([]),
  // Phase 9 — полнота ввода и человекочитаемая сводка
  completeness_pct: z.number().int().min(0).max(100).default(100),
  summary_text: z.string().default(""),
  // 2026-05-09 P2.3 — альтернативные кандидаты по другим брендам
  alternatives: z.array(pumpResultSchema).default([]),
  // 2026-05-10 — backend советует поправить ввод (afcea84 / 2beab6a)
  suggestions: z.array(inputSuggestionSchema).default([]),
});

export type SelectionResult = z.infer<typeof selectionResultSchema>;

export const segmentLabels: Record<"budget" | "mid" | "premium", string> = {
  budget: "Бюджет",
  mid: "Средний",
  premium: "Премиум",
};

export const triggerReasonLabels: Record<string, string> = {
  auto_q_high: "Высокий расход (Q > 500 м³/ч)",
  auto_h_high: "Высокий напор (H > 80 м)",
  auto_industrial: "Производственные стоки — нужно уточнение pH/абразива",
  auto_l_long_zhukovsky: "Длинная трасса (L > 500 м) — расчёт гидроудара по Жуковскому",
  auto_npsh_hot: "Горячая жидкость (T > 40 °C) — расчёт NPSH",
  auto_category_I: "I категория надёжности — сложная схема резервирования",
  auto_no_match: "Нет подходящих насосов в БД",
  auto_low_match_count: "Мало кандидатов в БД",
  auto_ex: "Требуется взрывозащита (Ex)",
};
