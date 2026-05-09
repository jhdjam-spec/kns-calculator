// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { useState } from "react";
import { ObjectTypeSelector } from "./ObjectTypeSelector";
import { AreaInput } from "./AreaInput";
import { CityAutocomplete } from "./CityAutocomplete";
import { SmartDefaultsPreview } from "./SmartDefaultsPreview";
import { StormMinimalResult, type StormMinimalResultData } from "./StormMinimalResult";
import { expandPreset, type ObjectTypeId } from "@/lib/storm/expandPreset";

interface FormState {
  objectTypeId: ObjectTypeId | null;
  area_ha: number | null;
  region_city: string | null;
}

const STORAGE_KEY = "inservo:kns:storm:minimal:draft";

function loadDraft(): FormState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as FormState;
  } catch {
    return null;
  }
}

function saveDraft(state: FormState): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // localStorage недоступен — игнорируем
  }
}

export function StormMinimalForm() {
  const [form, setForm] = useState<FormState>(() => {
    const draft = loadDraft();
    return (
      draft ?? {
        objectTypeId: null,
        area_ha: null,
        region_city: null,
      }
    );
  });
  const [result, setResult] = useState<StormMinimalResultData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = (patch: Partial<FormState>) => {
    setForm((prev) => {
      const next = { ...prev, ...patch };
      saveDraft(next);
      return next;
    });
  };

  const isValid =
    form.objectTypeId !== null &&
    form.area_ha !== null &&
    form.area_ha > 0 &&
    form.region_city !== null;

  const handleCalculate = async () => {
    if (!isValid || !form.objectTypeId || !form.area_ha || !form.region_city) return;

    setIsLoading(true);
    setError(null);
    try {
      const request = expandPreset({
        objectTypeId: form.objectTypeId,
        area_ha: form.area_ha,
        region_city: form.region_city,
      });

      const apiBase = process.env.NEXT_PUBLIC_API_BASE || "/api/backend";
      const response = await fetch(`${apiBase}/storm/calc`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const data = await response.json();
      setResult({
        Q_r_l_s: data.peak.Q_r_l_s,
        accumulator_volume_m3: data.recommendation.accumulator_volume_m3,
        los_capacity_l_s_min: data.recommendation.los_capacity_l_s_min,
        los_capacity_l_s_max: data.recommendation.los_capacity_l_s_max,
        Z_mid: data.peak.Z_mid,
        t_r_min: data.peak.t_r_min,
        sp_revision_used: data.sp_revision_used,
        region_data: data.region_data,
        inputs_summary: data.inputs_summary,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpgradeToClassical = () => {
    if (!form.objectTypeId || !form.area_ha || !form.region_city) return;
    const expanded = expandPreset({
      objectTypeId: form.objectTypeId,
      area_ha: form.area_ha,
      region_city: form.region_city,
    });
    if (typeof window !== "undefined") {
      localStorage.setItem(
        "inservo:kns:storm:classical:draft",
        JSON.stringify(expanded),
      );
      localStorage.setItem("inservo:kns:mode", "classical");
    }
    // Phase 20: переключение на Classical-форму
    alert(
      "Классический режим (Phase 20) ещё не реализован.\n\n" +
      "Параметры сохранены в localStorage — будут предзаполнены при появлении формы.",
    );
  };

  if (result && form.objectTypeId && form.area_ha && form.region_city) {
    return (
      <StormMinimalResult
        result={result}
        objectTypeId={form.objectTypeId}
        region_city={form.region_city}
        area_ha={form.area_ha}
        onEdit={() => setResult(null)}
        onUpgradeToClassical={handleUpgradeToClassical}
      />
    );
  }

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div>
        <h2 className="text-2xl font-display font-semibold text-ink-100 mb-1">
          🌧 Расчёт ливневой канализации — за 1 минуту
        </h2>
        <p className="text-sm text-ink-400">
          Метод предельных интенсивностей по СП 32.13330.2018 §6.2.4. Введите 3 параметра —
          получите пиковый расход Q<sub className="font-mono">r</sub> (л/с) и оценку
          стоимости комплекта.
        </p>
      </div>

      <div className="space-y-4 p-5 rounded-lg border border-white/10 bg-white/[0.02]">
        <ObjectTypeSelector
          selected={form.objectTypeId}
          onSelect={(id) => update({ objectTypeId: id })}
        />
        <AreaInput
          area_ha={form.area_ha}
          onChange={(area_ha) => update({ area_ha })}
        />
        <CityAutocomplete
          selected={form.region_city}
          onSelect={(city) => update({ region_city: city })}
        />
      </div>

      <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
        <button
          type="button"
          onClick={handleCalculate}
          disabled={!isValid || isLoading}
          className="px-5 py-3 rounded-md bg-accent-500 text-ink-950 font-medium hover:bg-accent-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? "Считаем..." : "Рассчитать пиковый расход →"}
        </button>
        {!isValid && (
          <p className="text-xs text-ink-500">Заполните все три поля</p>
        )}
      </div>

      {error && (
        <div className="p-3 rounded-md bg-red-500/10 border border-red-500/30 text-sm text-red-300">
          Ошибка расчёта: {error}
        </div>
      )}

      <SmartDefaultsPreview objectTypeId={form.objectTypeId} />
    </div>
  );
}
