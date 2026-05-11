// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { listPresets, type ObjectTypeId } from "@/lib/storm/expandPreset";

interface Props {
  selected: ObjectTypeId | null;
  onSelect: (id: ObjectTypeId) => void;
}

export function ObjectTypeSelector({ selected, onSelect }: Props) {
  const presets = listPresets();

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-ink-800 dark:text-ink-200">
        1. Что у вас за объект?
      </label>
      <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-7 gap-2">
        {presets.map((preset) => {
          const isSelected = selected === preset.id;
          return (
            <button
              key={preset.id}
              type="button"
              onClick={() => onSelect(preset.id)}
              title={preset.short_description}
              className={[
                "p-3 rounded-lg border text-center transition-all",
                "hover:border-brand-400 hover:bg-brand-50 dark:hover:border-accent-500 dark:hover:bg-accent-500/5",
                isSelected
                  ? "border-brand-600 bg-brand-50 ring-2 ring-brand-200 dark:border-accent-500 dark:bg-accent-500/10 dark:ring-accent-500/30"
                  : "border-ink-200 bg-ink-50 dark:border-white/10 dark:bg-white/[0.02]",
              ].join(" ")}
            >
              <div className="text-2xl mb-1" aria-hidden="true">
                {preset.icon}
              </div>
              <div className="text-xs leading-tight text-ink-700 dark:text-ink-300">
                {preset.label}
              </div>
            </button>
          );
        })}
      </div>
      {selected && (
        <p className="text-xs text-ink-700 dark:text-ink-400 mt-2">
          Выбрано:{" "}
          <span className="text-ink-900 dark:text-ink-200 font-medium">
            {presets.find((p) => p.id === selected)?.label}
          </span>
        </p>
      )}
    </div>
  );
}
