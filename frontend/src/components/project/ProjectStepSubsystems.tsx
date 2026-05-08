"use client";

import { useEffect } from "react";
import type { ProjectInput } from "@/lib/api-extended";
import { useProjectPresets } from "@/hooks/useProject";

interface Props {
  data: Partial<ProjectInput>;
  setData: (d: Partial<ProjectInput>) => void;
  onCalculate: () => void;
  onBack: () => void;
  isCalculating: boolean;
  error?: string;
}

const SUBSYSTEM_LABELS: Record<string, { title: string; description: string }> = {
  kns: { title: "КНС хозбытовая", description: "Канализационная насосная" },
  vns_potable: { title: "ВНС хозпитьевая", description: "Повысительная насосная для воды" },
  vns_fire: { title: "ВНС пожарная", description: "Насосная пожаротушения" },
  storm: { title: "Ливневая канализация", description: "Расчёт по СП 32 §6" },
  los: { title: "ЛОС биологическая", description: "Локальные очистные" },
  electrical: { title: "Электрика и шкаф", description: "ПУЭ + ТР ТС, подбор шкафа" },
  climate: { title: "Климат и заложение", description: "СП 131, СП 20 — глубина, нагрузки" },
  structural: { title: "Прочность корпуса", description: "Пригруз, толщина стенки" },
};

export function ProjectStepSubsystems({
  data,
  setData,
  onCalculate,
  onBack,
  isCalculating,
  error,
}: Props) {
  const presets = useProjectPresets();

  // Автозагрузка дефолтов из пресета (только при первом открытии шага)
  useEffect(() => {
    if (data.subsystems || !data.preset || !presets.data) return;
    const preset = presets.data.presets.find((p) => p.key === data.preset);
    if (preset) {
      setData({ ...data, subsystems: { ...preset.default_subsystems } });
    }
  }, [data, setData, presets.data]);

  const subs = data.subsystems || {};
  const toggle = (key: string) => {
    setData({
      ...data,
      subsystems: { ...subs, [key]: !subs[key] },
    });
  };

  return (
    <div>
      <h2 className="text-2xl font-display font-semibold text-ink-50 mb-2">
        Подсистемы для расчёта
      </h2>
      <p className="text-ink-400 mb-6 text-sm">
        Калькулятор автоматически выбрал подсистемы для пресета «{data.preset}».
        Можете включить/отключить вручную.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {Object.entries(SUBSYSTEM_LABELS).map(([key, label]) => {
          const isOn = !!subs[key];
          return (
            <button
              key={key}
              type="button"
              onClick={() => toggle(key)}
              className={`text-left p-4 rounded-lg border transition-all ${
                isOn
                  ? "bg-accent-500/10 border-accent-500"
                  : "bg-ink-950 border-ink-800 hover:border-ink-600"
              }`}
            >
              <div className="flex items-start gap-3">
                <div
                  className={`mt-0.5 size-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                    isOn ? "bg-accent-500 border-accent-500" : "border-ink-600"
                  }`}
                >
                  {isOn && <span className="text-ink-950 text-xs">✓</span>}
                </div>
                <div>
                  <div className="font-display font-semibold text-ink-50">{label.title}</div>
                  <div className="text-xs text-ink-400 mt-0.5">{label.description}</div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {error && (
        <div className="mt-6 p-4 bg-red-500/10 border border-red-500/30 rounded-md">
          <div className="text-red-400 font-medium">Ошибка расчёта</div>
          <div className="text-red-300 text-sm mt-1">{error}</div>
        </div>
      )}

      <div className="flex justify-between mt-8">
        <button
          type="button"
          onClick={onBack}
          className="text-ink-400 hover:text-ink-200 px-4 py-2 transition-colors"
        >
          ← Назад
        </button>
        <button
          type="button"
          onClick={onCalculate}
          disabled={isCalculating}
          className="bg-accent-500 hover:bg-accent-400 disabled:bg-ink-700 text-ink-950 px-6 py-2.5 rounded-md font-medium transition-colors"
        >
          {isCalculating ? "Расчёт…" : "Рассчитать проект →"}
        </button>
      </div>
    </div>
  );
}
