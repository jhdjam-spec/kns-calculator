// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { useState } from "react";
import { m2ToHa, haToM2 } from "@/lib/storm/expandPreset";

type Unit = "m2" | "ha";

interface Props {
  area_ha: number | null;
  onChange: (area_ha: number | null) => void;
}

const DEFAULT_AREA_M2 = 5000; // медианная парковка/двор

export function AreaInput({ area_ha, onChange }: Props) {
  const [unit, setUnit] = useState<Unit>("m2");

  const displayValue = (() => {
    if (area_ha === null) return "";
    return unit === "m2" ? String(Math.round(haToM2(area_ha))) : String(area_ha.toFixed(2));
  })();

  const handleChange = (raw: string) => {
    const num = parseFloat(raw.replace(",", "."));
    if (isNaN(num) || num <= 0) {
      onChange(null);
      return;
    }
    const ha = unit === "m2" ? m2ToHa(num) : num;
    onChange(ha);
  };

  const handleDontKnow = () => {
    setUnit("m2");
    onChange(m2ToHa(DEFAULT_AREA_M2));
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-ink-200">
        2. Какая площадь сбора?{" "}
        <span className="text-ink-500" title="Площадь территории, с которой собирается дождевая вода. Можно посчитать по плану — в м² (квадратных метрах) или га (гектарах).">
          ❓
        </span>
      </label>
      <div className="flex flex-wrap gap-2 items-center">
        <input
          type="text"
          inputMode="decimal"
          value={displayValue}
          onChange={(e) => handleChange(e.target.value)}
          placeholder={unit === "m2" ? "5000" : "0.5"}
          className="flex-1 min-w-[120px] px-3 py-2 rounded-md bg-white/[0.04] border border-white/10 text-ink-100 focus:border-accent-500 focus:outline-none"
        />
        <div className="flex rounded-md overflow-hidden border border-white/10" role="radiogroup" aria-label="Единица измерения">
          <button
            type="button"
            role="radio"
            aria-checked={unit === "m2"}
            onClick={() => setUnit("m2")}
            className={`px-3 py-2 text-sm ${unit === "m2" ? "bg-accent-500 text-ink-950" : "text-ink-400 hover:bg-white/5"}`}
          >
            м²
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={unit === "ha"}
            onClick={() => setUnit("ha")}
            className={`px-3 py-2 text-sm ${unit === "ha" ? "bg-accent-500 text-ink-950" : "text-ink-400 hover:bg-white/5"}`}
          >
            га
          </button>
        </div>
      </div>
      {area_ha !== null && (
        <p className="text-xs text-ink-400">
          {unit === "m2"
            ? `≈ ${area_ha.toFixed(3)} га`
            : `≈ ${haToM2(area_ha).toFixed(0)} м²`}
        </p>
      )}
      <button
        type="button"
        onClick={handleDontKnow}
        className="text-xs text-amber-400 hover:text-amber-300 underline-offset-2 hover:underline"
      >
        не знаю — взять типовое (5000 м²)
      </button>
    </div>
  );
}
