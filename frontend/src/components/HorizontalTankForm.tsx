"use client";

import { useState, useMemo } from "react";
import {
  STANDARD_DIAMETERS_MM,
  STANDARD_THICKNESSES_MM,
  calcHorizontalTank,
  type HorizontalTankInput,
  type HorizontalTankResult,
} from "@/lib/tankFormulas";

const DEFAULT_INPUT: HorizontalTankInput = {
  L_mm: 6000,
  D_mm: 2400,
  t_corpus_mm: 12,
  t_baffle_mm: 12,
  t_band_mm: 8,
  baffle_step_m: 1.5,
  bands_per_section: 2,
  profiles_per_baffle: 4,
  profiles_longitudinal: 6,
  price_pp_kg: 240,
  price_profile_m: 1060,
};

export function HorizontalTankForm() {
  const [input, setInput] = useState<HorizontalTankInput>(DEFAULT_INPUT);

  const result: HorizontalTankResult = useMemo(() => calcHorizontalTank(input), [input]);

  function update<K extends keyof HorizontalTankInput>(field: K, value: HorizontalTankInput[K]) {
    setInput((prev) => ({ ...prev, [field]: value }));
  }

  function NumberField({
    label, field, step = 1, min, max,
  }: {
    label: string;
    field: keyof HorizontalTankInput;
    step?: number;
    min?: number;
    max?: number;
  }) {
    return (
      <label className="flex flex-col text-sm">
        <span className="text-gray-700 mb-1">{label}</span>
        <input
          type="number"
          step={step}
          min={min}
          max={max}
          value={input[field]}
          onChange={(e) => update(field, Number(e.target.value) as never)}
          className="rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
        />
      </label>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Inputs */}
      <section>
        <h3 className="text-lg font-semibold mb-3">Параметры ёмкости</h3>
        <div className="grid grid-cols-2 gap-3">
          <NumberField label="Длина L, мм" field="L_mm" min={1500} max={20000} />

          <label className="flex flex-col text-sm">
            <span className="text-gray-700 mb-1">Диаметр D, мм</span>
            <select
              value={input.D_mm}
              onChange={(e) => update("D_mm", Number(e.target.value))}
              className="rounded-md border border-gray-300 px-3 py-2 bg-white"
            >
              {STANDARD_DIAMETERS_MM.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </label>

          <label className="flex flex-col text-sm">
            <span className="text-gray-700 mb-1">Толщина стенки, мм</span>
            <select
              value={input.t_corpus_mm}
              onChange={(e) => update("t_corpus_mm", Number(e.target.value))}
              className="rounded-md border border-gray-300 px-3 py-2 bg-white"
            >
              {STANDARD_THICKNESSES_MM.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>

          <label className="flex flex-col text-sm">
            <span className="text-gray-700 mb-1">Толщина перегородок, мм</span>
            <select
              value={input.t_baffle_mm}
              onChange={(e) => update("t_baffle_mm", Number(e.target.value))}
              className="rounded-md border border-gray-300 px-3 py-2 bg-white"
            >
              {STANDARD_THICKNESSES_MM.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>

          <label className="flex flex-col text-sm">
            <span className="text-gray-700 mb-1">Толщина бандажей, мм</span>
            <select
              value={input.t_band_mm}
              onChange={(e) => update("t_band_mm", Number(e.target.value))}
              className="rounded-md border border-gray-300 px-3 py-2 bg-white"
            >
              {STANDARD_THICKNESSES_MM.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>

          <NumberField label="Шаг перегородок, м" field="baffle_step_m" step={0.5} min={0.5} max={10} />
          <NumberField label="Обручей в секции" field="bands_per_section" min={0} max={10} />
          <NumberField label="Профилей на перегородке" field="profiles_per_baffle" min={2} max={10} />
          <NumberField label="Продольных профилей" field="profiles_longitudinal" min={2} max={10} />
        </div>

        <h4 className="text-sm font-semibold mt-5 mb-2 text-gray-700">Цены (₽/ед)</h4>
        <div className="grid grid-cols-2 gap-3">
          <NumberField label="ПП, ₽/кг" field="price_pp_kg" min={0} />
          <NumberField label="Профиль, ₽/м" field="price_profile_m" min={0} />
        </div>
      </section>

      {/* Outputs */}
      <section>
        <h3 className="text-lg font-semibold mb-3">Результат</h3>

        <div className="rounded-lg border-2 border-blue-300 bg-blue-50 p-5 mb-4">
          <div className="grid grid-cols-2 gap-y-2 text-sm">
            <span className="text-gray-600">Объём</span>
            <span className="font-semibold">{result.V_m3.toFixed(2)} м³</span>

            <span className="text-gray-600">Перегородок</span>
            <span className="font-semibold">{result.n_baffles} шт</span>

            <span className="text-gray-600">Масса корпуса</span>
            <span className="font-semibold">{result.mass_corpus_kg.toFixed(0)} кг</span>

            <span className="text-gray-600">Масса профилей</span>
            <span className="font-semibold">{result.mass_profiles_kg.toFixed(0)} кг</span>

            <span className="text-gray-600 font-medium">Масса общая</span>
            <span className="font-bold">{result.mass_total_kg.toFixed(0)} кг</span>
          </div>

          <hr className="my-3 border-blue-200" />

          <div className="grid grid-cols-2 gap-y-2 text-sm">
            <span className="text-gray-600">Стоимость ПП</span>
            <span className="font-semibold">{result.cost_pp_rub.toLocaleString("ru")} ₽</span>

            <span className="text-gray-600">Стоимость профилей</span>
            <span className="font-semibold">{result.cost_profiles_rub.toLocaleString("ru")} ₽</span>

            <span className="text-gray-700 font-medium text-base">Итого</span>
            <span className="font-bold text-base">
              {result.cost_total_rub.toLocaleString("ru")} ₽
            </span>
          </div>
        </div>

        <details className="text-xs text-gray-600 bg-gray-50 rounded p-3">
          <summary className="cursor-pointer font-medium">Промежуточные расчёты</summary>
          <dl className="mt-2 grid grid-cols-2 gap-y-1">
            <dt>Длина обручей</dt><dd>{result.length_bands_m.toFixed(1)} м</dd>
            <dt>Длина продольных профилей</dt><dd>{result.length_profiles_corpus_m.toFixed(1)} м</dd>
            <dt>Длина профилей на перегородках</dt><dd>{result.length_profiles_baffles_m.toFixed(1)} м</dd>
            <dt>Итого длина профилей</dt><dd>{result.length_profiles_total_m.toFixed(1)} м</dd>
            <dt>Листов на корпус</dt><dd>{result.sheets_corpus}</dd>
            <dt>Листов на перегородки</dt><dd>{result.sheets_baffles.toFixed(1)}</dd>
            <dt>Листов на бандажи</dt><dd>{result.sheets_bands}</dd>
          </dl>
        </details>

        {result.warnings.length > 0 && (
          <aside className="mt-4 rounded-md bg-yellow-50 border border-yellow-200 p-3 text-sm">
            <h4 className="font-semibold text-yellow-900">Предупреждения</h4>
            <ul className="list-disc pl-5 text-yellow-900">
              {result.warnings.map((w) => <li key={w}>{w}</li>)}
            </ul>
          </aside>
        )}

        <p className="mt-3 text-xs text-gray-500">
          Расчёт по технологическому калькулятору Серво-Юг (производственная ODS-модель).
          Это <strong>калькулятор стоимости</strong>, не прочности — толщина стенки и
          элементов задаётся вручную инженером.
        </p>
      </section>
    </div>
  );
}
