// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { AlertTriangle, Wrench } from "lucide-react";
import { getPreset, type ObjectTypeId } from "@/lib/storm/expandPreset";

export interface StormMinimalResultData {
  Q_r_l_s: number;
  accumulator_volume_m3: number;
  los_capacity_l_s_min: number;
  los_capacity_l_s_max: number;
  Z_mid: number;
  t_r_min: number;
  sp_revision_used: string;
  region_data: {
    q20_l_s_ha?: number;
    n?: number;
    gamma?: number;
  };
  inputs_summary: {
    F_total_ha: number;
    P_year: number;
  };
}

interface Props {
  result: StormMinimalResultData;
  objectTypeId: ObjectTypeId;
  region_city: string;
  area_ha: number;
  onEdit: () => void;
  onUpgradeToClassical: () => void;
}

const TOLERANCE_PCT = 30;

export function StormMinimalResult({
  result,
  objectTypeId,
  region_city,
  area_ha,
  onEdit,
  onUpgradeToClassical,
}: Props) {
  const preset = getPreset(objectTypeId);
  const Q_r = result.Q_r_l_s;
  const Q_r_min = Q_r * (1 - TOLERANCE_PCT / 100);
  const Q_r_max = Q_r * (1 + TOLERANCE_PCT / 100);
  const Q_r_m3h = (Q_r * 3.6).toFixed(0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-xl font-display font-semibold text-ink-900 dark:text-ink-100">
          {preset.icon} {preset.label} · {area_ha.toFixed(2)} га · {region_city}
        </h2>
        <button
          type="button"
          onClick={onEdit}
          className="text-sm text-ink-700 dark:text-ink-400 hover:text-brand-700 dark:hover:text-accent-500"
        >
          ← Изменить параметры
        </button>
      </div>

      {/* Главная цифра */}
      <div className="rounded-xl border border-brand-200 bg-brand-50 dark:border-accent-500/30 dark:bg-accent-500/5 p-6">
        <p className="text-sm text-ink-700 dark:text-ink-400 mb-2">Пиковый расход ливневых вод</p>
        <div className="flex items-baseline gap-3">
          <p className="text-4xl font-mono tabular-nums text-brand-700 dark:text-accent-500 font-semibold">
            {Q_r.toFixed(0)}
          </p>
          <p className="text-xl text-ink-700 dark:text-ink-300">л/с</p>
          <p className="text-sm text-ink-600 dark:text-ink-500">(≈ {Q_r_m3h} м³/час)</p>
        </div>
        <p className="text-xs text-ink-700 dark:text-ink-400 mt-3">
          Точность оценки: ±{TOLERANCE_PCT}% · Диапазон: {Q_r_min.toFixed(0)}…{Q_r_max.toFixed(0)} л/с
        </p>
      </div>

      {/* Что понадобится */}
      <div>
        <p className="text-sm font-medium text-ink-800 dark:text-ink-200 mb-3">
          Что вам понадобится по проекту
        </p>
        <ul className="space-y-2 text-sm text-ink-700 dark:text-ink-300">
          <li className="flex gap-2">
            <span aria-hidden="true">🛢</span>
            <span>
              Накопитель / резервуар КНС ≈ <strong>{result.accumulator_volume_m3.toFixed(0)} м³</strong>
            </span>
          </li>
          <li className="flex gap-2">
            <span aria-hidden="true">⚙</span>
            <span>
              Насосная станция Q ≈ <strong>{Q_r.toFixed(0)} л/с</strong>
            </span>
          </li>
          <li className="flex gap-2">
            <span aria-hidden="true">🌿</span>
            <span>
              {preset.los_required ? (
                <>
                  Очистные сооружения (ЛОС) — мощность{" "}
                  <strong>
                    {result.los_capacity_l_s_min.toFixed(0)}…{result.los_capacity_l_s_max.toFixed(0)} л/с
                  </strong>
                </>
              ) : (
                <>Очистные сооружения (ЛОС) — не требуются (сброс по СП 32 разрешён без очистки)</>
              )}
            </span>
          </li>
        </ul>
      </div>

      {/* Принятые допущения */}
      <div className="rounded-md border border-amber-300 bg-amber-50 dark:border-amber-500/30 dark:bg-amber-500/5 p-4 space-y-2">
        <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
          🟡 Принятые допущения (smart defaults)
        </p>
        <ul className="text-xs text-ink-700 dark:text-ink-300 space-y-1 ml-2">
          <li>• Редакция СП 32: {result.sp_revision_used}</li>
          <li>
            • Покрытие:{" "}
            {Object.entries(preset.surfaces)
              .map(([k, v]) => `${(v * 100).toFixed(0)}% ${k.replace("_share", "")}`)
              .join(", ")}
          </li>
          <li>• Время добегания τ = {result.t_r_min.toFixed(1)} мин</li>
          <li>• Период повторяемости P = {result.inputs_summary.P_year} {result.inputs_summary.P_year === 1 ? "год" : "года"}</li>
          {result.region_data.q20_l_s_ha && (
            <li>
              • Климат {region_city}: q20={result.region_data.q20_l_s_ha} л/с·га, n={result.region_data.n}
              {result.region_data.gamma && `, γ=${result.region_data.gamma}`}
            </li>
          )}
        </ul>
        <p className="text-xs text-amber-700 dark:text-amber-300 italic mt-2">
          ↑ Уточнить у инженера перед заказом оборудования
        </p>
      </div>

      {/* Внимание-плашка */}
      <div className="rounded-md border-2 border-amber-400 bg-amber-50 dark:bg-amber-400/10 p-4 flex gap-3" role="alert">
        <AlertTriangle size={20} className="shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
        <div className="text-sm text-ink-800 dark:text-ink-200">
          <p className="font-semibold mb-1">Это оценка для бюджета.</p>
          <p>
            Перед заказом инженер должен заполнить полный опросник (Классический режим).
            Точность Минимального режима ±{TOLERANCE_PCT}%.
          </p>
        </div>
      </div>

      {/* CTA */}
      <div className="flex flex-wrap gap-3 pt-2">
        <button
          type="button"
          onClick={onUpgradeToClassical}
          className="inline-flex items-center gap-2 px-5 py-3 rounded-md bg-brand-600 hover:bg-brand-700 text-white dark:bg-accent-500 dark:hover:bg-accent-400 dark:text-ink-950 font-medium transition-colors"
        >
          <Wrench size={16} strokeWidth={2.2} />
          Я инженер — открыть Классический режим
        </button>
      </div>
    </div>
  );
}
