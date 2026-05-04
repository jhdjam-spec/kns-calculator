"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  corpusMaterialLabels,
  qUnitLabels,
  wastewaterTypeLabels,
  wizardFormSchema,
  wizardFormToSelectionRequest,
  type CorpusMaterial,
  type WastewaterType,
  type WizardFormValues,
} from "@/schemas/input";
import { QHelper } from "./QHelper";

export interface WizardL0Props {
  onSubmit: (values: ReturnType<typeof wizardFormToSelectionRequest>) => void;
  isPending?: boolean;
}

const WASTEWATER_OPTIONS: WastewaterType[] = ["domestic", "drainage", "industrial"];
const CORPUS_OPTIONS: CorpusMaterial[] = ["pe", "glass"];

export function WizardL0({ onSubmit, isPending = false }: WizardL0Props) {
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitted },
  } = useForm<WizardFormValues>({
    resolver: zodResolver(wizardFormSchema),
    defaultValues: {
      Q_unit: "m3h",
      // Опциональные поля по умолчанию пусты — backend подставит дефолт
      wastewater_type: "" as unknown as WastewaterType,
      corpus_material: "pe",
    },
    mode: "onSubmit",
  });

  // Подсказка от QHelper — что было подставлено через помощник по типу объекта
  const [qHint, setQHint] = useState<string | null>(null);

  return (
    <form
      onSubmit={handleSubmit((values) => onSubmit(wizardFormToSelectionRequest(values)))}
      className="space-y-5 max-w-xl"
      aria-label="Форма подбора насоса L0"
      noValidate
    >
      {/* Помощник по типу объекта (Q-калькулятор по СП 30) */}
      <QHelper
        onCalculate={(Q, description) => {
          setValue("Q_value", Q, { shouldValidate: true });
          setValue("Q_unit", "m3h");
          setQHint(description);
        }}
      />

      {/* Q + единица */}
      <div>
        <label htmlFor="Q_value" className="block text-sm font-medium mb-1">
          Расход <span className="text-red-600">*</span>
        </label>
        <div className="flex gap-2">
          <input
            id="Q_value"
            type="number"
            step="any"
            inputMode="decimal"
            placeholder="Например: 21.2"
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
            aria-invalid={!!errors.Q_value}
            {...register("Q_value")}
          />
          <select
            aria-label="Единицы расхода"
            className="rounded-md border border-gray-300 px-3 py-2 bg-white"
            {...register("Q_unit")}
          >
            {(Object.keys(qUnitLabels) as Array<keyof typeof qUnitLabels>).map((u) => (
              <option key={u} value={u}>
                {qUnitLabels[u]}
              </option>
            ))}
          </select>
        </div>
        {qHint && (
          <p className="mt-1 text-xs text-blue-700">
            ✓ Подставлено из помощника: {qHint}
          </p>
        )}
        {errors.Q_value && (
          <p className="mt-1 text-sm text-red-600" role="alert">
            {errors.Q_value.message}
          </p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          Сколько кубометров стоков в час в самый загруженный момент. Если знаете только суточный объём — переключите единицы (м³/сут), пересчитаем сами.
        </p>
      </div>

      {/* dH */}
      <div>
        <label htmlFor="dH_m" className="block text-sm font-medium mb-1">
          Перепад высот, м{" "}
          <span className="text-gray-400 text-xs font-normal">(если не знаете — оставьте пустым)</span>
        </label>
        <input
          id="dH_m"
          type="number"
          step="any"
          inputMode="decimal"
          placeholder="Например: 10"
          className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
          aria-invalid={!!errors.dH_m}
          {...register("dH_m")}
        />
        {errors.dH_m && (
          <p className="mt-1 text-sm text-red-600" role="alert">
            {errors.dH_m.message}
          </p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          На сколько метров выше точки сброса находится самая нижняя точка стоков. Не знаете — поставьте 8–10 м с запасом, инженер уточнит по геодезии.
        </p>
      </div>

      {/* L */}
      <div>
        <label htmlFor="L_m" className="block text-sm font-medium mb-1">
          Длина напорной трассы, м{" "}
          <span className="text-gray-400 text-xs font-normal">(если не знаете — оставьте пустым)</span>
        </label>
        <input
          id="L_m"
          type="number"
          step="any"
          inputMode="decimal"
          placeholder="Например: 100. Поставьте 0 если КНС стоит вплотную к коллектору"
          className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
          aria-invalid={!!errors.L_m}
          {...register("L_m")}
        />
        {errors.L_m && (
          <p className="mt-1 text-sm text-red-600" role="alert">
            {errors.L_m.message}
          </p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          Расстояние от насоса до точки сброса (коллектор водоканала, ЛОС, водоём). Длинные трассы (более 500 м) — передадим инженеру для дополнительного расчёта.
        </p>
      </div>

      {/* Тип стоков */}
      <fieldset>
        <legend className="block text-sm font-medium mb-1">
          Тип стоков{" "}
          <span className="text-gray-400 text-xs font-normal">(не выбрано — будет «бытовая канализация»)</span>
        </legend>
        <div className="space-y-2">
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="radio"
              value=""
              className="mt-1"
              defaultChecked
              {...register("wastewater_type")}
            />
            <span>
              <span className="font-medium text-gray-500">Не выбрано</span>
              <span className="block text-xs text-gray-400">
                Подставим «бытовая канализация» — самый частый случай
              </span>
            </span>
          </label>
          {WASTEWATER_OPTIONS.map((opt) => (
            <label key={opt} className="flex items-start gap-2 cursor-pointer">
              <input
                type="radio"
                value={opt}
                className="mt-1"
                {...register("wastewater_type")}
              />
              <span>
                <span className="font-medium">{wastewaterTypeLabels[opt]}</span>
                <span className="block text-xs text-gray-500">
                  {opt === "domestic" && "Дома, гостиницы, офисы, кафе, апартаменты"}
                  {opt === "drainage" && "Дождевая вода и дренаж (чистая вода без волокон)"}
                  {opt === "industrial" && "Промышленные стоки (с песком, химией, агрессивные)"}
                </span>
              </span>
            </label>
          ))}
        </div>
        {errors.wastewater_type && (
          <p className="mt-1 text-sm text-red-600" role="alert">
            {errors.wastewater_type.message}
          </p>
        )}
      </fieldset>

      {/* Материал корпуса (L1) */}
      <fieldset>
        <legend className="block text-sm font-medium mb-1">
          Материал корпуса КНС{" "}
          <span className="text-gray-400 text-xs font-normal">(влияет на цену)</span>
        </legend>
        <div className="flex flex-wrap gap-4">
          {CORPUS_OPTIONS.map((opt) => (
            <label key={opt} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                value={opt}
                {...register("corpus_material")}
              />
              <span className="text-sm">{corpusMaterialLabels[opt]}</span>
            </label>
          ))}
        </div>
        <p className="mt-1 text-xs text-gray-500">
          ПЭ — стандарт Серво-Юг (любой типоразмер под заказ).
          Стеклопластик — 5 стандартных диаметров от 800 до 2400 мм, дешевле для малых объектов.
        </p>
      </fieldset>

      {/* Sticky на мобильных — чтобы не скроллить вверх к кнопке */}
      <div className="sticky bottom-0 -mx-4 px-4 py-3 bg-white/90 backdrop-blur border-t border-gray-200 md:static md:mx-0 md:px-0 md:py-0 md:bg-transparent md:backdrop-blur-none md:border-0">
        <button
          type="submit"
          disabled={isPending}
          className="w-full md:w-auto rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold px-6 py-3 shadow-sm transition"
        >
          {isPending ? "Подбираю варианты..." : "Подобрать насос"}
        </button>

        {isSubmitted && Object.keys(errors).length > 0 && (
          <p className="text-sm text-red-600 mt-1" role="alert">
            Заполните обязательные поля.
          </p>
        )}
      </div>
    </form>
  );
}
