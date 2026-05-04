"use client";

import type { SelectionResult } from "@/schemas/result";
import { PumpCard } from "./PumpCard";

export interface ResultsCardsProps {
  result: SelectionResult;
}

export function ResultsCards({ result }: ResultsCardsProps) {
  const { results, computed, candidates_total, warnings, assumptions } = result;

  return (
    <section aria-label="Результаты подбора" className="space-y-5">
      <header>
        <h2 className="text-2xl font-bold">Топ-3 насоса</h2>
        <p className="text-sm text-gray-600 mt-1">
          Расчёт: D = <strong>{computed.D_mm} мм</strong>, v = {computed.v_ms.toFixed(2)} м/с,{" "}
          H<sub>full</sub> = <strong>{computed.H_full_m.toFixed(1)} м</strong> (потери трения{" "}
          {computed.H_tr_m.toFixed(1)} м, местные {computed.H_m_m.toFixed(1)} м, запас{" "}
          {(computed.safety_factor * 100).toFixed(0)}%)
        </p>
        <p className="text-xs text-gray-500 mt-1">
          Кандидатов после фильтрации: {candidates_total}
        </p>
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
