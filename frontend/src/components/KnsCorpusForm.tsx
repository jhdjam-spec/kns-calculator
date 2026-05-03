"use client";

import { useState, useMemo } from "react";
import {
  STANDARD_DIAMETERS_MM,
  STANDARD_THICKNESSES_MM,
  calcKnsCorpus,
  suggestKnsWallThickness,
  type KnsCorpusInput,
  type KnsCorpusResult,
} from "@/lib/tankFormulas";

const DEFAULT_INPUT: KnsCorpusInput = {
  D_mm: 1590,
  H_mm: 3400,
  t_wall_mm: 12,
  t_dome_mm: 12,
  price_pp_kg: 240,
};

export function KnsCorpusForm() {
  const [input, setInput] = useState<KnsCorpusInput>(DEFAULT_INPUT);
  const result: KnsCorpusResult = useMemo(() => calcKnsCorpus(input), [input]);
  const recommendedThickness = suggestKnsWallThickness(input.H_mm);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <section>
        <h3 className="text-lg font-semibold mb-3">Параметры корпуса КНС</h3>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col text-sm">
            <span className="text-gray-700 mb-1">Диаметр D, мм</span>
            <select
              value={input.D_mm}
              onChange={(e) => setInput((p) => ({ ...p, D_mm: Number(e.target.value) }))}
              className="rounded-md border border-gray-300 px-3 py-2 bg-white"
            >
              {STANDARD_DIAMETERS_MM.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </label>

          <label className="flex flex-col text-sm">
            <span className="text-gray-700 mb-1">Высота H, мм</span>
            <input
              type="number"
              step={100}
              min={1000}
              max={8000}
              value={input.H_mm}
              onChange={(e) => setInput((p) => ({ ...p, H_mm: Number(e.target.value) }))}
              className="rounded-md border border-gray-300 px-3 py-2"
            />
          </label>

          <label className="flex flex-col text-sm">
            <span className="text-gray-700 mb-1">
              Толщина стенки, мм{" "}
              <span className="text-xs text-blue-600">(рекоменд. {recommendedThickness})</span>
            </span>
            <select
              value={input.t_wall_mm}
              onChange={(e) => setInput((p) => ({ ...p, t_wall_mm: Number(e.target.value) }))}
              className="rounded-md border border-gray-300 px-3 py-2 bg-white"
            >
              {STANDARD_THICKNESSES_MM.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>

          <label className="flex flex-col text-sm">
            <span className="text-gray-700 mb-1">Толщина дна/крышки, мм</span>
            <select
              value={input.t_dome_mm}
              onChange={(e) => setInput((p) => ({ ...p, t_dome_mm: Number(e.target.value) }))}
              className="rounded-md border border-gray-300 px-3 py-2 bg-white"
            >
              {STANDARD_THICKNESSES_MM.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>

          <label className="flex flex-col text-sm col-span-2">
            <span className="text-gray-700 mb-1">Цена ПП, ₽/кг</span>
            <input
              type="number"
              min={0}
              value={input.price_pp_kg}
              onChange={(e) => setInput((p) => ({ ...p, price_pp_kg: Number(e.target.value) }))}
              className="rounded-md border border-gray-300 px-3 py-2"
            />
          </label>
        </div>

        <p className="mt-3 text-xs text-gray-500">
          Стандартные типоразмеры из реальных проектов:{" "}
          D1500/H3200 (малый), D1590/H3400 (АртВинд Мысхако), D2000/H4000 (средний),
          D4200/H4010 (КНС 70 л/с).
        </p>
      </section>

      <section>
        <h3 className="text-lg font-semibold mb-3">Результат</h3>

        <div className="rounded-lg border-2 border-blue-300 bg-blue-50 p-5 mb-4">
          <div className="grid grid-cols-2 gap-y-2 text-sm">
            <span className="text-gray-600">Объём корпуса</span>
            <span className="font-semibold">{result.V_m3.toFixed(2)} м³</span>

            <span className="text-gray-600">H/D</span>
            <span className="font-semibold">{result.H_to_D.toFixed(2)}</span>

            <span className="text-gray-600">Листов на стенку</span>
            <span className="font-semibold">{result.sheets_wall}</span>

            <span className="text-gray-600">Листов на дно/крышку</span>
            <span className="font-semibold">{result.sheets_dome}</span>

            <span className="text-gray-600 font-medium">Масса корпуса</span>
            <span className="font-bold">{result.mass_total_kg.toFixed(0)} кг</span>

            <span className="text-gray-700 font-medium text-base">Стоимость ПП</span>
            <span className="font-bold text-base">
              {result.cost_pp_rub.toLocaleString("ru")} ₽
            </span>
          </div>
        </div>

        {result.warnings.length > 0 && (
          <aside className="rounded-md bg-yellow-50 border border-yellow-200 p-3 text-sm">
            <h4 className="font-semibold text-yellow-900">Предупреждения</h4>
            <ul className="list-disc pl-5 text-yellow-900 space-y-1">
              {result.warnings.map((w) => <li key={w}>{w}</li>)}
            </ul>
          </aside>
        )}

        <p className="mt-3 text-xs text-gray-500">
          Только материал корпуса (стенка + дно + крышка). НЕ включено: люк ревизионный,
          вентиляция, кабельные/трубные вводы, якорная плита, монтаж, доставка.
          Толщина рекомендуется по эмпирике (см.{" "}
          <code>tank_calculator_models.json</code>) — для глубоких корпусов нужен расчёт
          бокового давления грунта.
        </p>
      </section>
    </div>
  );
}
