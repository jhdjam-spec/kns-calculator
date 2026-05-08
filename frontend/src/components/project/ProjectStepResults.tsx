"use client";

import type { ProjectResult, SubsystemResult } from "@/lib/api-extended";

interface Props {
  result: ProjectResult;
  onBack: () => void;
  onRestart: () => void;
}

export function ProjectStepResults({ result, onBack, onRestart }: Props) {
  const subsystems: Array<[string, SubsystemResult | null]> = [
    ["КНС хозбытовая", result.kns],
    ["ВНС хозпитьевая", result.vns_potable],
    ["ВНС пожарная", result.vns_fire],
    ["Ливневая канализация", result.storm],
    ["ЛОС биологическая", result.los],
    ["Электрика", result.electrical],
    ["Климат", result.climate],
    ["Прочность", result.structural],
  ];

  const active = subsystems.filter(([, r]) => r !== null);

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-display font-semibold text-ink-50 mb-1">
            {result.project_name}
          </h2>
          <p className="text-ink-400 text-sm">
            Пресет: {result.preset} · Подсистем: {active.length}
            {result.total_warnings > 0 && (
              <span className="ml-3 text-yellow-400">
                ⚠ {result.total_warnings} предупреждений
              </span>
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={onRestart}
          className="text-sm text-ink-400 hover:text-accent-500 transition-colors"
        >
          Новый проект
        </button>
      </div>

      {/* Карточки подсистем */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {active.map(([label, subResult]) => (
          <SubsystemCard key={label} label={label} result={subResult!} />
        ))}
      </div>

      {/* Ссылки на нормативы */}
      {result.references_consolidated.length > 0 && (
        <div className="bg-ink-950 border border-ink-800 rounded-lg p-5 mb-6">
          <div className="font-display font-semibold text-ink-50 mb-3">
            Нормативная база
          </div>
          <ul className="text-sm text-ink-300 space-y-1.5">
            {result.references_consolidated.map((ref, i) => (
              <li key={i}>
                <span className="text-accent-500 font-mono">{ref.regulation_code}</span>
                {ref.section && <span className="text-ink-500"> · {ref.section}</span>}
                {ref.purpose && <span className="text-ink-400"> — {ref.purpose}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Действия */}
      <div className="flex flex-col md:flex-row gap-3 mb-6">
        <button
          type="button"
          disabled
          title="В разработке"
          className="bg-ink-800 text-ink-500 px-4 py-2.5 rounded-md cursor-not-allowed"
        >
          📄 Скачать PDF расчётной записки
        </button>
        <button
          type="button"
          disabled
          title="В разработке"
          className="bg-ink-800 text-ink-500 px-4 py-2.5 rounded-md cursor-not-allowed"
        >
          📊 Экспорт BOM в CSV
        </button>
      </div>

      {/* Beta предупреждение */}
      <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-md text-sm">
        <span className="text-yellow-400 font-medium">Бета-версия. </span>
        <span className="text-yellow-200">
          Результаты являются информационными. Перед применением в проекте обязательна
          верификация инженером-проектировщиком ВК. Допуск ±15% от реальной документации.
        </span>
      </div>

      <div className="flex justify-between mt-8">
        <button
          type="button"
          onClick={onBack}
          className="text-ink-400 hover:text-ink-200 px-4 py-2 transition-colors"
        >
          ← Изменить параметры
        </button>
      </div>
    </div>
  );
}

function SubsystemCard({ label, result }: { label: string; result: SubsystemResult }) {
  const statusColor: Record<string, string> = {
    ok: "text-green-400 border-green-500/30 bg-green-500/5",
    warning: "text-yellow-400 border-yellow-500/30 bg-yellow-500/5",
    error: "text-red-400 border-red-500/30 bg-red-500/5",
    skipped: "text-ink-500 border-ink-700 bg-ink-900",
  };
  const statusIcon: Record<string, string> = {
    ok: "✓",
    warning: "⚠",
    error: "✕",
    skipped: "—",
  };

  return (
    <div className={`border rounded-lg p-4 ${statusColor[result.status] || statusColor.skipped}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="font-display font-semibold text-ink-50">{label}</div>
        <span className="font-mono text-lg">{statusIcon[result.status]}</span>
      </div>
      <div className="text-sm text-ink-300 mb-2">{result.summary}</div>
      {result.warnings && result.warnings.length > 0 && (
        <div className="mt-3 pt-3 border-t border-ink-800/50">
          <div className="text-xs text-yellow-400 font-medium mb-1">Предупреждения:</div>
          <ul className="text-xs text-ink-400 space-y-0.5">
            {result.warnings.map((w, i) => (
              <li key={i}>• {w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
