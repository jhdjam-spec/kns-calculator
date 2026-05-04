"use client";

import type { SelectionResult } from "@/schemas/result";
import { PumpCard } from "./PumpCard";

export interface ResultsCardsProps {
  result: SelectionResult;
}

export function ResultsCards({ result }: ResultsCardsProps) {
  const { results, computed, candidates_total, warnings, assumptions, summary_text, completeness_pct } = result;

  // Phase 9: цвет полосы прогресса по полноте ввода
  const completenessColor =
    completeness_pct >= 80 ? "bg-green-500" :
    completeness_pct >= 50 ? "bg-yellow-500" :
    "bg-orange-500";

  return (
    <section aria-label="Результаты подбора" className="space-y-5">
      <header>
        <h2 className="text-2xl font-bold">Подобрали 3 варианта</h2>

        {/* Phase 9: человекочитаемая сводка */}
        {summary_text && (
          <p className="text-sm text-gray-700 mt-2 leading-relaxed">
            {summary_text}
          </p>
        )}

        {/* Phase 9: индикатор полноты ввода */}
        <div className="mt-3 flex items-center gap-3">
          <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full ${completenessColor} transition-all`}
              style={{ width: `${completeness_pct}%` }}
              title={`Заполнено ${completeness_pct}% параметров`}
            />
          </div>
          <span className="text-xs text-gray-600 whitespace-nowrap">
            Данных: {completeness_pct}%
            {completeness_pct < 70 && (
              <span className="text-orange-600 ml-1">
                — заполните параметры для точности
              </span>
            )}
          </span>
        </div>

        <details className="mt-2 text-xs text-gray-500">
          <summary className="cursor-pointer hover:text-gray-700 select-none">
            Детали расчёта (для инженера) →
          </summary>
          <div className="mt-1.5 pl-3 space-y-0.5">
            <p>
              Подобран диаметр напорной трубы: <strong>{computed.D_mm} мм</strong>{" "}
              (скорость потока {computed.v_ms.toFixed(2)} м/с)
            </p>
            <p>
              Полный напор насоса: <strong>{computed.H_full_m.toFixed(1)} м</strong>
              {" — "}
              из них потери трения {computed.H_tr_m.toFixed(1)} м, местные {computed.H_m_m.toFixed(1)} м,
              запас {(computed.safety_factor * 100).toFixed(0)}%
            </p>
            <p>Прошло фильтрацию: {candidates_total} насосов из БД</p>
          </div>
        </details>
      </header>

      {assumptions.length > 0 && (
        <aside className="rounded-md bg-blue-50 border border-blue-200 p-3">
          <h4 className="text-sm font-semibold text-blue-900 mb-1">
            Подставленные значения
          </h4>
          <p className="text-xs text-blue-800 mb-1">
            Часть полей не заполнена — калькулятор использовал безопасные дефолты:
          </p>
          <ul className="text-sm text-blue-900 list-disc pl-5">
            {assumptions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </aside>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <PumpCard segment="budget" pump={results.budget} />
        <PumpCard segment="mid" pump={results.mid} />
        <PumpCard segment="premium" pump={results.premium} />
      </div>

      {warnings.length > 0 && (
        <aside className="rounded-md bg-yellow-50 border border-yellow-200 p-3">
          <h4 className="text-sm font-semibold text-yellow-900 mb-1">Предупреждения</h4>
          <ul className="text-sm text-yellow-900 list-disc pl-5">
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </aside>
      )}
    </section>
  );
}
