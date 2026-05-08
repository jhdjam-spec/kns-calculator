"use client";

import type { ProjectInput, ProjectPresetMeta } from "@/lib/api-extended";

interface Props {
  data: Partial<ProjectInput>;
  setData: (d: Partial<ProjectInput>) => void;
  presets: ProjectPresetMeta[];
  isLoading: boolean;
  onNext: () => void;
}

export function ProjectStepPreset({ data, setData, presets, isLoading, onNext }: Props) {
  if (isLoading) {
    return <div className="text-ink-400">Загрузка пресетов…</div>;
  }

  return (
    <div>
      <h2 className="text-2xl font-display font-semibold text-ink-50 mb-2">
        Какой объект вы проектируете?
      </h2>
      <p className="text-ink-400 mb-6 text-sm">
        Выберите тип — и калькулятор автоматически подберёт нужные расчёты.
        Можно будет изменить вручную на следующем шаге.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {presets.map((p) => (
          <button
            key={p.key}
            type="button"
            onClick={() => setData({ ...data, preset: p.key })}
            className={`text-left p-4 rounded-lg border transition-all ${
              data.preset === p.key
                ? "bg-accent-500/10 border-accent-500"
                : "bg-ink-950 border-ink-800 hover:border-ink-600"
            }`}
          >
            <div className="font-display font-semibold text-ink-50 mb-1">{p.title}</div>
            <div className="text-xs text-ink-400">{p.description}</div>
          </button>
        ))}
      </div>

      <div className="flex justify-end mt-6">
        <button
          type="button"
          onClick={onNext}
          disabled={!data.preset}
          className="bg-accent-500 hover:bg-accent-400 disabled:bg-ink-700 disabled:text-ink-500 text-ink-950 px-6 py-2.5 rounded-md font-medium transition-colors"
        >
          Далее →
        </button>
      </div>
    </div>
  );
}
