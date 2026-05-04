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
  {
    id: "dormitory",
    label: "Общежитие",
    description: "Постоянное проживание с общими удобствами — 100 л/сут на жильца",
    litres_per_unit_per_day: 100,
    k_gen: 2.5,
    unit_label: "жильцов",
    typical_units: "обычно 50–300",
  },
  {
    id: "hospital",
    label: "Больница / поликлиника",
    description: "Койка с уходом — 200 л/сут (СП 30 А.2)",
    litres_per_unit_per_day: 200,
    k_gen: 2.5,
    unit_label: "коек",
    typical_units: "обычно 50–500",
  },
  {
    id: "kindergarten",
    label: "Детский сад / ясли",
    description: "Ребёнок дневного пребывания — 75 л/сут",
    litres_per_unit_per_day: 75,
    k_gen: 2.5,
    unit_label: "детей",
    typical_units: "обычно 50–300",
  },
  {
    id: "sport",
    label: "Спорткомплекс / фитнес",
    description: "Спортсмен (с душевыми) — 60 л/сут",
    litres_per_unit_per_day: 60,
    k_gen: 2.5,
    unit_label: "посетителей в день",
    typical_units: "обычно 100–1000",
  },
  {
    id: "laundry",
    label: "Прачечная",
    description: "На 1 кг сухого белья — 60 л (промышленная прачечная)",
    litres_per_unit_per_day: 60,
    k_gen: 2.0,
    unit_label: "кг белья в сутки",
    typical_units: "обычно 100–2000",
  },
  {
    id: "carwash",
    label: "Автомойка",
    description: "Мойка одного автомобиля — 200 л (с замкнутым циклом — меньше)",
    litres_per_unit_per_day: 200,
    k_gen: 2.5,
    unit_label: "автомобилей в сутки",
    typical_units: "обычно 30–300",
  },
  {
    id: "industrial_workshop",
    label: "Промышленный цех",
    description: "Сотрудник смены (с душевыми) — 60 л + технологическая вода уточняется отдельно",
    litres_per_unit_per_day: 60,
    k_gen: 1.8,
    unit_label: "сотрудников смены",
    typical_units: "обычно 50–500",
  },
  {
    id: "warehouse",
    label: "Склад / логистика",
    description: "Сотрудник без душевых — 16 л/сут",
    litres_per_unit_per_day: 16,
    k_gen: 2.5,
    unit_label: "сотрудников",
    typical_units: "обычно 20–200",
  },
  {
    id: "campsite",
    label: "Кемпинг / гостевые дома",
    description: "Койко-место с общими удобствами — 50 л/сут",
    litres_per_unit_per_day: 50,
    k_gen: 3.0,
    unit_label: "койко-мест",
    typical_units: "обычно 20–200",
  },
  {
    id: "bath_sauna",
    label: "Баня / сауна",
    description: "Посетитель — 240 л/сут (с душем и парной)",
    litres_per_unit_per_day: 240,
    k_gen: 2.5,
    unit_label: "посетителей в день",
    typical_units: "обычно 30–200",
  },
  {
    id: "gas_station",
    label: "АЗС / придорожный комплекс",
    description: "Посетитель — 25 л/сут (туалет + кафе)",
    litres_per_unit_per_day: 25,
    k_gen: 2.5,
    unit_label: "посетителей в день",
    typical_units: "обычно 100–1500",
  },
  {
    id: "housing_complex",
    label: "Жилой комплекс / микрорайон",
    description: "На квартиру (3 жителя × 200 л + полив территории) — 700 л/сут",
    litres_per_unit_per_day: 700,
    k_gen: 2.0,
    unit_label: "квартир",
    typical_units: "обычно 200–3000",
  },
  {
    id: "cottage_village",
    label: "Коттеджный посёлок",
    description: "На дом (4 жителя × 230 л) — 920 л/сут",
    litres_per_unit_per_day: 920,
    k_gen: 3.0,
    unit_label: "домохозяйств",
    typical_units: "обычно 30–500",
  },
  {
    id: "mall_large",
    label: "ТРЦ / гипермаркет (большой)",
    description: "Площадь × 4 л/м² в сутки (фуд-корт + санузлы + клининг)",
    litres_per_unit_per_day: 4,
    k_gen: 2.0,
    unit_label: "м² торговой площади",
    typical_units: "обычно 5000–80000",
  },
  {
    id: "airport_station",
    label: "Аэропорт / ж/д вокзал",
    description: "Пассажир в день — 8 л (туалеты + общепит + клининг)",
    litres_per_unit_per_day: 8,
    k_gen: 2.0,
    unit_label: "пассажиров в день",
    typical_units: "обычно 5000–100000",
  },
];

/**
 * Расчёт дождевой канализации (drainage) — по площади водосбора и
 * интенсивности дождя для региона. СП 32.13330.2018 п. 7.4-7.10.
 *
 * Q (л/с) = ψ × q20 × F × β    где:
 *   ψ — коэф. стока (асфальт 0.95, газон 0.10, кровля 1.0, среднее 0.6-0.8)
 *   q20 — интенсивность дождя 20 мин для региона, л/с·га
 *   F — площадь водосбора, га
 *   β — коэф. учёта неравномерности, обычно 0.65-0.85
 *
 * Возвращает Q в м³/ч (для совместимости с калькулятором КНС).
 */
interface RegionRain {
  id: string;
  label: string;
  q20: number; // л/с·га, СП 32 карта 1
}

const RAIN_REGIONS: RegionRain[] = [
  { id: "south_krd", label: "Юг РФ (Краснодар, Ростов, Сочи)", q20: 90 },
  { id: "south_volga", label: "Поволжье (Волгоград, Астрахань)", q20: 70 },
  { id: "moscow", label: "Москва, центр РФ", q20: 80 },
  { id: "spb_north", label: "Санкт-Петербург, Северо-Запад", q20: 60 },
  { id: "ural", label: "Урал (Екатеринбург, Челябинск)", q20: 65 },
  { id: "siberia", label: "Сибирь (Новосибирск, Красноярск)", q20: 55 },
  { id: "far_east", label: "Дальний Восток (Хабаровск, Владивосток)", q20: 95 },
];

interface SurfaceType {
  id: string;
  label: string;
  psi: number;
}

const SURFACE_TYPES: SurfaceType[] = [
  { id: "asphalt", label: "Асфальт / дороги / парковки", psi: 0.95 },
  { id: "roof", label: "Кровля зданий", psi: 1.0 },
  { id: "mixed_urban", label: "Смешанная городская (среднее)", psi: 0.7 },
  { id: "lawn", label: "Газоны / зелёная зона", psi: 0.1 },
  { id: "gravel", label: "Гравий / щебень", psi: 0.4 },
];

function calculateDrainageQ(area_ha: number, q20: number, psi: number): number {
  // Q (л/с) = ψ × q20 × F × β    где β=0.75 типичное усреднение
  const beta = 0.75;
  const Q_ls = psi * q20 * area_ha * beta;
  // л/с → м³/ч: × 3.6
  const Q_m3h = Q_ls * 3.6;
  return Math.round(Q_m3h * 10) / 10;
}

function calculateQ(preset: ObjectPreset, units: number): number {
  const Q_avg_m3h = (units * preset.litres_per_unit_per_day) / 1000 / 24;
  const Q_peak = Q_avg_m3h * preset.k_gen;
  // Округление до 1 знака
  return Math.round(Q_peak * 10) / 10;
}

type Mode = "domestic" | "drainage";

export function QHelper({ onCalculate }: QHelperProps) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<Mode>("domestic");

  // Domestic state
  const [presetId, setPresetId] = useState<string>("hotel");
  const [units, setUnits] = useState<string>("");

  // Drainage state
  const [regionId, setRegionId] = useState<string>("south_krd");
  const [surfaceId, setSurfaceId] = useState<string>("mixed_urban");
  const [areaM2, setAreaM2] = useState<string>("");

  const preset = PRESETS.find((p) => p.id === presetId)!;
  const unitsNum = parseFloat(units);
  const isDomesticValid = !isNaN(unitsNum) && unitsNum > 0;
  const domesticQ = isDomesticValid ? calculateQ(preset, unitsNum) : null;

  const region = RAIN_REGIONS.find((r) => r.id === regionId)!;
  const surface = SURFACE_TYPES.find((s) => s.id === surfaceId)!;
  const areaM2Num = parseFloat(areaM2);
  const isDrainageValid = !isNaN(areaM2Num) && areaM2Num > 0;
  const areaHa = isDrainageValid ? areaM2Num / 10000 : 0;
  const drainageQ = isDrainageValid
    ? calculateDrainageQ(areaHa, region.q20, surface.psi)
    : null;

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
          {/* Режим: бытовые/промышленные стоки или дождевая канализация */}
          <div role="tablist" className="flex gap-1 rounded-md bg-blue-100 p-1">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "domestic"}
              onClick={() => setMode("domestic")}
              className={clsx(
                "flex-1 rounded px-3 py-1.5 text-xs font-medium transition",
                mode === "domestic"
                  ? "bg-white text-blue-900 shadow-sm"
                  : "text-blue-700 hover:bg-blue-50"
              )}
            >
              Бытовые / промышленные
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "drainage"}
              onClick={() => setMode("drainage")}
              className={clsx(
                "flex-1 rounded px-3 py-1.5 text-xs font-medium transition",
                mode === "drainage"
                  ? "bg-white text-blue-900 shadow-sm"
                  : "text-blue-700 hover:bg-blue-50"
              )}
            >
              Дождевая канализация
            </button>
          </div>

          {mode === "domestic" && (
            <>
              <p className="text-xs text-gray-600">
                Расчёт по нормам водоотведения СП 30.13330.2020 Прил. А +
                коэффициент часовой неравномерности по СП 32.13330.2018.
              </p>

              {/* Тип объекта */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Тип объекта
                </label>
                <select
                  aria-label="Тип объекта"
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
                  <span className="text-gray-400 font-normal">
                    ({preset.typical_units})
                  </span>
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

              {domesticQ !== null && (
                <div className="rounded-md bg-white border border-blue-200 p-3">
                  <p className="text-xs text-gray-600 mb-1">
                    Расчётный пиковый расход:
                  </p>
                  <p className="text-2xl font-bold text-blue-900">
                    {domesticQ} м³/ч
                  </p>
                  <p className="text-[10px] text-gray-500 mt-1">
                    {unitsNum} × {preset.litres_per_unit_per_day} л/сут × коэф.
                    неравномерности {preset.k_gen} ÷ 24 ч
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      onCalculate(
                        domesticQ,
                        `${preset.label}, ${unitsNum} ${preset.unit_label}`
                      );
                      setOpen(false);
                    }}
                    className="mt-2 w-full rounded-md py-2 px-3 text-sm font-medium transition bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    Подставить в форму расчёта
                  </button>
                </div>
              )}
            </>
          )}

          {mode === "drainage" && (
            <>
              <p className="text-xs text-gray-600">
                Расчёт по СП 32.13330.2018 п. 7.4-7.10:
                Q&nbsp;=&nbsp;ψ×q₂₀×F×β, где F — площадь водосбора (га).
              </p>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Регион (для интенсивности дождя q₂₀)
                </label>
                <select
                  aria-label="Регион"
                  value={regionId}
                  onChange={(e) => setRegionId(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                >
                  {RAIN_REGIONS.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.label} (q₂₀ = {r.q20} л/с·га)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Тип поверхности (коэф. стока ψ)
                </label>
                <select
                  aria-label="Тип поверхности"
                  value={surfaceId}
                  onChange={(e) => setSurfaceId(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                >
                  {SURFACE_TYPES.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label} (ψ = {s.psi})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Площадь водосбора, м²{" "}
                  <span className="text-gray-400 font-normal">
                    (1 га = 10 000 м²)
                  </span>
                </label>
                <input
                  type="number"
                  step="any"
                  inputMode="decimal"
                  value={areaM2}
                  onChange={(e) => setAreaM2(e.target.value)}
                  placeholder="Например, 50000 (5 га)"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                />
              </div>

              {drainageQ !== null && (
                <div className="rounded-md bg-white border border-blue-200 p-3">
                  <p className="text-xs text-gray-600 mb-1">
                    Расчётный максимальный приток дождевых стоков:
                  </p>
                  <p className="text-2xl font-bold text-blue-900">
                    {drainageQ} м³/ч
                  </p>
                  <p className="text-[10px] text-gray-500 mt-1">
                    F = {areaHa.toFixed(2)} га × ψ = {surface.psi} × q₂₀ = {region.q20}{" "}
                    л/с·га × β = 0.75 × 3.6 → м³/ч
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      onCalculate(
                        drainageQ,
                        `Дождевая, ${areaM2Num.toLocaleString("ru")} м² (${surface.label.toLowerCase()}, ${region.label})`
                      );
                      setOpen(false);
                    }}
                    className="mt-2 w-full rounded-md py-2 px-3 text-sm font-medium transition bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    Подставить в форму расчёта
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
