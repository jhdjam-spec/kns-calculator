"use client";

import type { ProjectInput } from "@/lib/api-extended";

interface Props {
  data: Partial<ProjectInput>;
  setData: (d: Partial<ProjectInput>) => void;
  onNext: () => void;
  onBack: () => void;
}

const RUSSIAN_CITIES = [
  "Москва", "Санкт-Петербург", "Краснодар", "Сочи", "Ростов-на-Дону",
  "Симферополь", "Ялта", "Ставрополь", "Воронеж", "Казань", "Самара",
  "Уфа", "Пермь", "Екатеринбург", "Челябинск", "Новосибирск", "Красноярск",
  "Иркутск", "Хабаровск", "Владивосток", "Якутск", "Магадан",
];

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
      <h2 className="text-2xl font-display font-semibold text-ink-50 mb-2">
        Базовые параметры
      </h2>
      <p className="text-ink-400 mb-6 text-sm">
        Эти данные автоматически подставятся во все расчёты.
        Точность калькулятора ±15% от реального проекта.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Название проекта */}
        <Field label="Название проекта">
          <input
            type="text"
            className="form-input"
            value={data.project_name || ""}
            onChange={(e) => setData({ ...data, project_name: e.target.value })}
          />
        </Field>

        <Field label="Шифр (опционально)">
          <input
            type="text"
            className="form-input"
            value={data.project_code || ""}
            onChange={(e) => setData({ ...data, project_code: e.target.value })}
            placeholder="Например, БМ.12-КД-НК"
          />
        </Field>

        {/* Город */}
        <Field label="Город (для климата и нормативов)">
          <select
            className="form-input"
            value={data.region_city || "Краснодар"}
            onChange={(e) => setData({ ...data, region_city: e.target.value })}
          >
            {RUSSIAN_CITIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </Field>

        {/* Заказчик */}
        <Field label="Заказчик (опционально)">
          <input
            type="text"
            className="form-input"
            value={data.customer || ""}
            onChange={(e) => setData({ ...data, customer: e.target.value })}
          />
        </Field>

        {/* Население */}
        <Field
          label="Расчётное число пользователей"
          hint="Жители для ИЖС/ЖК · Сотрудники для офиса · Койки для больницы"
        >
          <input
            type="number"
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
            className="form-input"
            value={data.floors || 1}
            min={1}
            onChange={(e) => setData({ ...data, floors: Number(e.target.value) })}
          />
        </Field>

        {/* Объём */}
        <Field
          label="Объём здания, м³"
          hint="Для табл. 1 СП 8.13130 (расход на пожаротушение)"
        >
          <input
            type="number"
            className="form-input"
            value={data.volume_m3 || 0}
            min={0}
            onChange={(e) => setData({ ...data, volume_m3: Number(e.target.value) })}
          />
        </Field>

        {/* Площадь */}
        <Field label="Площадь территории, м²">
          <input
            type="number"
            className="form-input"
            value={data.area_m2 || 0}
            min={0}
            onChange={(e) => setData({ ...data, area_m2: Number(e.target.value) })}
          />
        </Field>

        {/* Грунт */}
        <Field label="Тип грунта">
          <select
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
        <Field label="УГВ ниже 1 м">
          <label className="flex items-center gap-2 mt-2">
            <input
              type="checkbox"
              checked={data.has_groundwater || false}
              onChange={(e) => setData({ ...data, has_groundwater: e.target.checked })}
              className="size-4 accent-accent-500"
            />
            <span className="text-sm text-ink-300">
              Высокий УГВ — потребуется пригруз корпуса
            </span>
          </label>
        </Field>

        {/* ATEX */}
        <Field label="ATEX зона">
          <label className="flex items-center gap-2 mt-2">
            <input
              type="checkbox"
              checked={data.is_atex_zone || false}
              onChange={(e) => setData({ ...data, is_atex_zone: e.target.checked })}
              className="size-4 accent-accent-500"
            />
            <span className="text-sm text-ink-300">
              Взрывоопасная зона (нефтехимия, фильтрат ТКО)
            </span>
          </label>
        </Field>
      </div>

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
          onClick={onNext}
          className="bg-accent-500 hover:bg-accent-400 text-ink-950 px-6 py-2.5 rounded-md font-medium transition-colors"
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
      <label className="block text-sm text-ink-300 mb-1.5">{label}</label>
      {children}
      {hint && <div className="text-xs text-ink-500 mt-1">{hint}</div>}
    </div>
  );
}
