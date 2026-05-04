"use client";

import { useState } from "react";
import clsx from "clsx";

/**
 * Помощник по типу объекта — рассчитывает Q (м³/ч пиковый) из понятных
 * параметров: «гостиница 50 номеров», «частный дом 4 жителя» и т.д.
 *
 * Источник норм: СП 30.13330.2020 «Внутренние водопровод и канализация»
 * Приложение А Таблица А.2. Коэффициент часовой неравномерности K_gen.max
 * по СП 32.13330.2018 Таблица 1.
 *
 * Формула: Q_ч_пик = (N × q_сут_удел / 1000 / 24) × K_gen
 *   где q_сут_удел — литров на единицу в сутки (СП 30 А.2)
 *         K_gen — коэф. часовой неравномерности (СП 32 табл.1)
 */

export interface QHelperProps {
  /** Колбэк при выборе пресета и расчёте Q */
  onCalculate: (Q_m3h: number, description: string) => void;
}

interface ObjectPreset {
  id: string;
  label: string;
  description: string;
  /** Литров в сутки на единицу */
  litres_per_unit_per_day: number;
  /** Коэф. часовой неравномерности (СП 32 табл.1) */
  k_gen: number;
  /** Минимум единиц для расчёта */
  unit_label: string;
  /** Типичный диапазон, для подсказки в плейсхолдере */
  typical_units: string;
}

const PRESETS: ObjectPreset[] = [
  {
    id: "private_house",
    label: "Частный дом / коттедж",
    description: "Постоянное проживание, душ, ванна, стиральная машина",
    litres_per_unit_per_day: 230,
    k_gen: 4.5,
    unit_label: "жителей",
    typical_units: "обычно 2–6",
  },
  {
    id: "apartments",
    label: "Многоквартирный дом",
    description: "Жильцы — 200 л/сут на человека (СП 30 А.2)",
    litres_per_unit_per_day: 200,
    k_gen: 2.5,
    unit_label: "жителей",
    typical_units: "обычно 50–500",
  },
  {
    id: "hotel",
    label: "Гостиница / отель",
    description: "Номер с душем — 200 л/сут на гостя",
    litres_per_unit_per_day: 250,
    k_gen: 2.5,
    unit_label: "номеров",
    typical_units: "обычно 20–200",
  },
  {
    id: "office",
    label: "Офис / БЦ",
    description: "Сотрудник за рабочий день — 16 л/сут",
    litres_per_unit_per_day: 16,
    k_gen: 2.5,
    unit_label: "сотрудников",
    typical_units: "обычно 50–500",
  },
  {
    id: "cafe",
    label: "Кафе / ресторан",
    description: "Посадочное место — 12 л/сут (без приготовления горячих блюд)",
    litres_per_unit_per_day: 12,
    k_gen: 2.0,
    unit_label: "посадочных мест",
    typical_units: "обычно 20–200",
  },
  {
    id: "school",
    label: "Школа / учебное",
    description: "Учащийся / преподаватель — 10 л/сут",
    litres_per_unit_per_day: 10,
    k_gen: 2.5,
    unit_label: "учащихся",
    typical_units: "обычно 200–1500",
  },
  {
    id: "shopping",
    label: "ТРЦ / магазин",
    description: "Покупатель в день — 5 л/сут (только санузлы)",
    litres_per_unit_per_day: 5,
    k_gen: 2.5,
    unit_label: "посетителей в день",
    typical_units: "обычно 500–5000",
  },
];

function calculateQ(preset: ObjectPreset, units: number): number {
  const Q_avg_m3h = (units * preset.litres_per_unit_per_day) / 1000 / 24;
  const Q_peak = Q_avg_m3h * preset.k_gen;
  // Округление до 1 знака
  return Math.round(Q_peak * 10) / 10;
}

export function QHelper({ onCalculate }: QHelperProps) {
  const [open, setOpen] = useState(false);
  const [presetId, setPresetId] = useState<string>("hotel");
  const [units, setUnits] = useState<string>("");

  const preset = PRESETS.find((p) => p.id === presetId)!;
  const unitsNum = parseFloat(units);
  const isValid = !isNaN(unitsNum) && unitsNum > 0;
  const calculatedQ = isValid ? calculateQ(preset, unitsNum) : null;

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-3">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-sm font-medium text-blue-900 hover:text-blue-700 w-full"
      >
        <span>{open ? "▼" : "▶"}</span>
        <span>Не знаете расход в м³/ч? Подобрать по типу объекта →</span>
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          <p className="text-xs text-gray-600">
            Расчёт по нормам водоотведения СП 30.13330.2020 + коэффициент часовой
            неравномерности по СП 32.13330.2018.
          </p>

          {/* Тип объекта */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Тип объекта
            </label>
            <select
              value={presetId}
              onChange={(e) => setPresetId(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
            >
              {PRESETS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">{preset.description}</p>
          </div>

          {/* Количество единиц */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Количество {preset.unit_label}{" "}
              <span className="text-gray-400 font-normal">({preset.typical_units})</span>
            </label>
            <input
              type="number"
              step="any"
              inputMode="decimal"
              value={units}
              onChange={(e) => setUnits(e.target.value)}
              placeholder="Введите число"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>

          {/* Расчётный Q */}
          {calculatedQ !== null && (
            <div className="rounded-md bg-white border border-blue-200 p-3">
              <p className="text-xs text-gray-600 mb-1">Расчётный пиковый расход:</p>
              <p className="text-2xl font-bold text-blue-900">
                {calculatedQ} м³/ч
              </p>
              <p className="text-[10px] text-gray-500 mt-1">
                {unitsNum} × {preset.litres_per_unit_per_day} л/сут × коэф. неравномерности {preset.k_gen} ÷ 24 ч
              </p>
              <button
                type="button"
                onClick={() => {
                  onCalculate(
                    calculatedQ,
                    `${preset.label}, ${unitsNum} ${preset.unit_label}`
                  );
                  setOpen(false);
                }}
                className={clsx(
                  "mt-2 w-full rounded-md py-2 px-3 text-sm font-medium transition",
                  "bg-blue-600 hover:bg-blue-700 text-white"
                )}
              >
                Подставить в форму расчёта
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
