// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { getPreset, type ObjectTypeId } from "@/lib/storm/expandPreset";

interface Props {
  objectTypeId: ObjectTypeId | null;
}

const SURFACE_LABELS: Record<string, string> = {
  asphalt_share: "асфальт",
  concrete_share: "бетон",
  roof_share: "кровля",
  paving_dense_share: "брусчатка плотная",
  paving_loose_share: "брусчатка с расшивкой",
  gravel_share: "гравий",
  crushed_stone_share: "щебень",
  soil_share: "грунт",
  lawn_share: "газон",
  forest_share: "лесопарк",
  water_share: "вода",
};

export function SmartDefaultsPreview({ objectTypeId }: Props) {
  if (!objectTypeId) return null;
  const preset = getPreset(objectTypeId);

  const surfacesText = Object.entries(preset.surfaces)
    .map(([k, v]) => `${SURFACE_LABELS[k] ?? k} ${(v * 100).toFixed(0)}%`)
    .join(" + ");

  return (
    <div className="text-xs text-ink-700 dark:text-ink-400 space-y-1 p-3 rounded-md bg-ink-50 border border-ink-200 dark:bg-white/[0.02] dark:border-white/[0.06]">
      <p className="text-ink-800 dark:text-ink-300 font-medium">
        Что мы подставим автоматически (видно в отчёте):
      </p>
      <ul className="space-y-0.5 ml-2">
        <li>• Редакция СП 32 — 2018 (актуальная)</li>
        <li>• Покрытие — {surfacesText}</li>
        <li>• Время добегания — {preset.t_concentration_min} мин</li>
        <li>• Период повторяемости — P={preset.period_P_year} {preset.period_P_year === 1 ? "год" : "года"}</li>
      </ul>
      <p className="text-ink-600 dark:text-ink-500 italic mt-1">{preset.rationale}</p>
    </div>
  );
}
