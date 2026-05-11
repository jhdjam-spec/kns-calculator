"use client";

import type { ProjectInput } from "@/lib/api-extended";
import { ClimateSimulator } from "@/components/wizard/ClimateSimulator";

interface Props {
  data: Partial<ProjectInput>;
  setData: (d: Partial<ProjectInput>) => void;
  onNext: () => void;
  onBack: () => void;
}

// RUSSIAN_CITIES заменены на динамический список из ClimateSimulator (Phase 28
// pulls 76 городов из 02_dataset/regulations/climate_cities_2026.json via
// GET /climate/cities). Fallback "Краснодар" остался.

const SOILS = [
  { key: "clay_loam", label: "Суглинок (стандартный)" },
  { key: "sand_dry", label: "Песок сухой" },
  { key: "sand_wet", label: "Песок водонасыщенный" },
  { key: "clay", label: "Глина" },
  { key: "rocky", label: "Скальный" },
  { key: "peat", label: "Торф / органика" },
];

export function ProjectStepParams({ data, setData, onNext, onBack }: Props) {
  return (
    <div>
      <h2 className="text-2xl font-display font-semibold text-ink-900 dark:text-ink-50 mb-2">
        Базовые параметры
      </h2>
      <p className="text-ink-700 dark:text-ink-400 mb-6 text-sm">
        Эти данные автоматически подставятся во все расчёты.
        Точность калькулятора ±15% от реального проекта.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Название проекта */}
        <Field label="Название проекта">
          <input
            type="text"
            aria-label="Название проекта"
            className="form-input"
            value={data.project_name || ""}
            onChange={(e) => setData({ ...data, project_name: e.target.value })}
          />
        </Field>

        <Field label="Шифр (опционально)">
          <input
            type="text"
            aria-label="Шифр проекта"
            className="form-input"
            value={data.project_code || ""}
            onChange={(e) => setData({ ...data, project_code: e.target.value })}
            placeholder="Например, БМ.12-КД-НК"
          />
        </Field>

        {/* Город — Climate Simulator (Phase 28) */}
        <div className="md:col-span-2">
          <ClimateSimulator
            value={data.region_city || "Краснодар"}
            onChange={(city) => setData({ ...data, region_city: city })}
          />
        </div>

        {/* Заказчик */}
        <Field label="Заказчик (опционально)">
          <input
            type="text"
            aria-label="Заказчик"
            className="form-input"
            value={data.customer || ""}
            onChange={(e) => setData({ ...data, customer: e.target.value })}
          />
        </Field>

        {/* Население */}
        <Field
          label="Расчётное число пользователей, чел"
          hint="Жители (ИЖС/ЖК) · сотрудники (офис) · койки (больница) · посадочные места (кафе). Норма потребления — СП 30 прил. А.2"
        >
          <input
            type="number"
            aria-label="Расчётное число пользователей"
            className="form-input"
            value={data.population || 0}
            min={0}
            onChange={(e) => setData({ ...data, population: Number(e.target.value) })}
          />
        </Field>

        {/* Этажность */}
        <Field label="Этажность">
          <input
            type="number"
            aria-label="Этажность"
            className="form-input"
            value={data.floors || 1}
            min={1}
            onChange={(e) => setData({ ...data, floors: Number(e.target.value) })}
          />
        </Field>

        {/* Объём */}
        <Field
          label="Объём здания, м³"
          hint="Определяет расход воды на пожаротушение по табл. 1 СП 8.13130 и группу спринклерных установок"
        >
          <input
            type="number"
            aria-label="Объём здания, м³"
            className="form-input"
            value={data.volume_m3 || 0}
            min={0}
            onChange={(e) => setData({ ...data, volume_m3: Number(e.target.value) })}
          />
        </Field>

        {/* Площадь */}
        <Field
          label="Площадь территории, м²"
          hint="Для расчёта ливневой канализации (СП 32 §6) и площади кровли"
        >
          <input
            type="number"
            aria-label="Площадь территории, м²"
            className="form-input"
            value={data.area_m2 || 0}
            min={0}
            onChange={(e) => setData({ ...data, area_m2: Number(e.target.value) })}
          />
        </Field>

        {/* Грунт */}
        <Field label="Тип грунта">
          <select
            aria-label="Тип грунта"
            className="form-input"
            value={data.soil_type || "clay_loam"}
            onChange={(e) => setData({ ...data, soil_type: e.target.value })}
          >
            {SOILS.map((s) => (
              <option key={s.key} value={s.key}>{s.label}</option>
            ))}
          </select>
        </Field>

        {/* УГВ */}
        <Field
          label="УГВ — уровень грунтовых вод"
          hint="Если УГВ выше дна корпуса — нужен пригруз бетоном (СП 32 §6.3, K=1.1)"
        >
          <label className="flex items-center gap-2 mt-2">
            <input
              type="checkbox"
              checked={data.has_groundwater || false}
              onChange={(e) => setData({ ...data, has_groundwater: e.target.checked })}
              className="size-4 accent-accent-500"
            />
            <span className="text-sm text-ink-700 dark:text-ink-300">
              Высокий УГВ (ниже 1 м от поверхности)
            </span>
          </label>
        </Field>

        {/* ATEX */}
        <Field
          label="Взрывоопасная зона (ATEX)"
          hint="Зоны B-1а / IIB-T3 — нефтехимия, АЗС, фильтрат ТКО. Шкаф +35-45% к цене (ТР ТС 012/2011)"
        >
          <label className="flex items-center gap-2 mt-2">
            <input
              type="checkbox"
              checked={data.is_atex_zone || false}
              onChange={(e) => setData({ ...data, is_atex_zone: e.target.checked })}
              className="size-4 accent-accent-500"
            />
            <span className="text-sm text-ink-700 dark:text-ink-300">
              Объект во взрывоопасной зоне
            </span>
          </label>
        </Field>
      </div>

      <div className="flex justify-between mt-8">
        <button
          type="button"
          onClick={onBack}
          className="text-ink-700 dark:text-ink-400 hover:text-ink-900 dark:hover:text-ink-200 px-4 py-2 transition-colors"
        >
          ← Назад
        </button>
        <button
          type="button"
          onClick={onNext}
          className="bg-brand-600 hover:bg-brand-700 text-white dark:bg-accent-500 dark:hover:bg-accent-400 dark:text-ink-950 px-6 py-2.5 rounded-md font-medium transition-colors"
        >
          Далее →
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm text-ink-700 dark:text-ink-300 mb-1.5">{label}</label>
      {children}
      {hint && <div className="text-xs text-ink-600 dark:text-ink-500 mt-1">{hint}</div>}
    </div>
  );
}
