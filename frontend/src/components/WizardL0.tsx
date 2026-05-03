"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  qUnitLabels,
  wastewaterTypeLabels,
  wizardFormSchema,
  wizardFormToL0Input,
  type WastewaterType,
  type WizardFormValues,
} from "@/schemas/input";

export interface WizardL0Props {
  onSubmit: (values: ReturnType<typeof wizardFormToL0Input>) => void;
  isPending?: boolean;
}

const WASTEWATER_OPTIONS: WastewaterType[] = ["domestic", "drainage", "industrial"];

export function WizardL0({ onSubmit, isPending = false }: WizardL0Props) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitted },
  } = useForm<WizardFormValues>({
    resolver: zodResolver(wizardFormSchema),
    defaultValues: {
      Q_unit: "m3h",
      wastewater_type: "domestic",
    },
    mode: "onSubmit",
  });

  return (
    <form
      onSubmit={handleSubmit((values) => onSubmit(wizardFormToL0Input(values)))}
      className="space-y-5 max-w-xl"
      aria-label="Форма подбора насоса L0"
      noValidate
    >
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
        {errors.Q_value && (
          <p className="mt-1 text-sm text-red-600" role="alert">
            {errors.Q_value.message}
          </p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          Пиковый расход стоков. Для м³/сут применяйте K_gen вручную или попросите инженера.
        </p>
      </div>

      {/* dH */}
      <div>
        <label htmlFor="dH_m" className="block text-sm font-medium mb-1">
          Перепад точек ΔH, м <span className="text-red-600">*</span>
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
          Геометрический напор: уровень жидкости в приёмном резервуаре → точка сброса.
        </p>
      </div>

      {/* L */}
      <div>
        <label htmlFor="L_m" className="block text-sm font-medium mb-1">
          Длина напорной трассы L, м <span className="text-red-600">*</span>
        </label>
        <input
          id="L_m"
          type="number"
          step="any"
          inputMode="decimal"
          placeholder="0 — если только внутренняя обвязка"
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
          При L &gt; 500 м расчёт гидроудара (Жуковский) обязателен — будет передано инженеру.
        </p>
      </div>

      {/* Тип стоков */}
      <fieldset>
        <legend className="block text-sm font-medium mb-1">
          Тип стоков <span className="text-red-600">*</span>
        </legend>
        <div className="space-y-2">
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
                  {opt === "domestic" && "Квартирные стоки, гостиницы, офисы — нужен свободный проход ≥ 50 мм"}
                  {opt === "drainage" && "Чистая ливнёвка, дренаж — допустимы насосы со свободным проходом ≥ 10 мм"}
                  {opt === "industrial" && "С включениями, абразивом, pH ≠ 7 — обязательно уточнение у инженера"}
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

      <button
        type="submit"
        disabled={isPending}
        className="w-full md:w-auto rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium px-6 py-3 transition"
      >
        {isPending ? "Подбираю..." : "Подобрать насос"}
      </button>

      {isSubmitted && Object.keys(errors).length > 0 && (
        <p className="text-sm text-red-600" role="alert">
          Заполните все обязательные поля корректно.
        </p>
      )}
    </form>
  );
}
