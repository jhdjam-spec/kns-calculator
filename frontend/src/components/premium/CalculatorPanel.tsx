"use client";

import { useState } from "react";
import clsx from "clsx";
import { Settings2, HelpCircle } from "lucide-react";
import {
  type WastewaterType,
  wastewaterTypeLabels,
  type QUnit,
  type CorpusMaterial,
} from "@/schemas/input";
import { toM3h } from "@/lib/units";
import type { SelectionResult } from "@/schemas/result";
import { QHelper } from "@/components/QHelper";

interface CalculatorPanelProps {
  onSubmit: (params: {
    Q_m3h: number;
    dH_m?: number;
    L_m?: number;
    wastewater_type?: WastewaterType;
    corpus_material?: CorpusMaterial;
  }) => void;
  isPending?: boolean;
  result?: SelectionResult | null;
}

const wastewaterPills: { id: WastewaterType; label: string }[] = [
  { id: "domestic", label: "Бытовая" },
  { id: "drainage", label: "Дождевая" },
  { id: "industrial", label: "Промышл." },
  { id: "clean_water", label: "СПД" },
  { id: "fire_protection", label: "Пожар." },
];

const corpusPills: { id: CorpusMaterial; label: string }[] = [
  { id: "pe", label: "Полиэтилен" },
  { id: "glass", label: "Стеклопластик" },
];

export function CalculatorPanel({ onSubmit, isPending, result }: CalculatorPanelProps) {
  const [qValue, setQValue] = useState("21.2");
  const [qUnit, setQUnit] = useState<QUnit>("m3h");
  const [dH, setDH] = useState("8");
  const [L, setL] = useState("120");
  const [wastewater, setWastewater] = useState<WastewaterType>("domestic");
  const [corpus, setCorpus] = useState<CorpusMaterial>("pe");
  const [advanced, setAdvanced] = useState(false);
  const [helperOpen, setHelperOpen] = useState(false);

  const handleSubmit = () => {
    const Q_num = parseFloat(qValue);
    if (!Q_num || Q_num <= 0) return;
    onSubmit({
      Q_m3h: toM3h(Q_num, qUnit),
      dH_m: dH ? parseFloat(dH) : undefined,
      L_m: L ? parseFloat(L) : undefined,
      wastewater_type: wastewater,
      corpus_material: corpus,
    });
  };

  return (
    <section id="calculator" className="py-24 md:py-32 bg-ink-950 relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(ellipse 800px 400px at 50% 0%, rgba(30, 58, 95, 0.4), transparent 70%)",
        }}
      />

      <div className="relative max-w-7xl mx-auto px-5 md:px-10">
        <div className="mb-12 max-w-2xl">
          <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-ink-300 mb-4">
            <span className="block w-6 h-px bg-accent-500" />
            ПОДБОР
          </div>
          <h2 className="font-display text-3xl md:text-5xl font-semibold text-ink-50 leading-tight tracking-tight">
            Введите параметры объекта
          </h2>
          <p className="mt-4 text-ink-300 text-lg">
            Расчёт inline в реальном времени. Результат — топ-3 насоса с диапазоном цены.
          </p>
        </div>

        <div className="rounded-block bg-white/[0.025] border border-white/[0.08] p-6 md:p-10 backdrop-blur-sm">
          <div className="grid lg:grid-cols-12 gap-8 lg:gap-12">
            {/* Left: form */}
            <div className="lg:col-span-5 space-y-6">
              {/* Тип объекта */}
              <div>
                <div className="text-[10px] font-mono uppercase tracking-wider text-ink-400 mb-3">
                  Тип стоков
                </div>
                <div className="flex flex-wrap gap-2">
                  {wastewaterPills.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setWastewater(p.id)}
                      className={clsx(
                        "px-3 py-2 rounded-md text-sm transition-all duration-base",
                        wastewater === p.id
                          ? "bg-ink-50 text-ink-950 font-medium"
                          : "bg-white/5 text-ink-300 hover:bg-white/10",
                      )}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Q + unit */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label
                    htmlFor="calc-q"
                    className="text-[10px] font-mono uppercase tracking-wider text-ink-400"
                  >
                    Расход Q
                  </label>
                  <button
                    type="button"
                    onClick={() => setHelperOpen(!helperOpen)}
                    className="inline-flex items-center gap-1 text-xs text-accent-500 hover:text-accent-400 transition-colors"
                  >
                    <HelpCircle size={12} strokeWidth={1.75} />
                    Не знаю Q
                  </button>
                </div>
                <div className="flex gap-2">
                  <input
                    id="calc-q"
                    type="number"
                    inputMode="decimal"
                    value={qValue}
                    onChange={(e) => setQValue(e.target.value)}
                    step="0.1"
                    className="flex-1 h-12 px-3 rounded-md bg-white/5 border border-white/10 text-ink-50 font-mono tabular-nums focus:border-accent-500 outline-none transition-colors"
                  />
                  <div className="flex bg-white/5 rounded-md p-1 gap-0.5">
                    {(["m3h", "ls", "m3sut"] as QUnit[]).map((u) => (
                      <button
                        key={u}
                        type="button"
                        onClick={() => setQUnit(u)}
                        className={clsx(
                          "px-3 text-xs font-mono rounded transition-colors",
                          qUnit === u
                            ? "bg-ink-50 text-ink-950"
                            : "text-ink-400 hover:text-ink-200",
                        )}
                      >
                        {u === "m3h" ? "м³/ч" : u === "ls" ? "л/с" : "м³/сут"}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Advanced toggle */}
              <button
                type="button"
                onClick={() => setAdvanced(!advanced)}
                className="inline-flex items-center gap-2 text-sm text-ink-300 hover:text-accent-500 transition-colors"
              >
                <Settings2 size={14} strokeWidth={1.5} />
                {advanced ? "Скрыть" : "Расширенные параметры"}
              </button>

              {advanced && (
                <div className="space-y-5 pt-2 border-t border-white/[0.06]">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label
                        htmlFor="calc-dh"
                        className="block text-[10px] font-mono uppercase tracking-wider text-ink-400 mb-2"
                      >
                        Перепад dH, м
                      </label>
                      <input
                        id="calc-dh"
                        type="number"
                        value={dH}
                        onChange={(e) => setDH(e.target.value)}
                        step="0.5"
                        className="w-full h-11 px-3 rounded-md bg-white/5 border border-white/10 text-ink-50 font-mono tabular-nums focus:border-accent-500 outline-none transition-colors"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="calc-l"
                        className="block text-[10px] font-mono uppercase tracking-wider text-ink-400 mb-2"
                      >
                        Длина L, м
                      </label>
                      <input
                        id="calc-l"
                        type="number"
                        value={L}
                        onChange={(e) => setL(e.target.value)}
                        step="1"
                        className="w-full h-11 px-3 rounded-md bg-white/5 border border-white/10 text-ink-50 font-mono tabular-nums focus:border-accent-500 outline-none transition-colors"
                      />
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] font-mono uppercase tracking-wider text-ink-400 mb-2">
                      Материал корпуса
                    </div>
                    <div className="flex gap-2">
                      {corpusPills.map((p) => (
                        <button
                          key={p.id}
                          type="button"
                          onClick={() => setCorpus(p.id)}
                          className={clsx(
                            "px-3 py-2 rounded-md text-sm transition-all",
                            corpus === p.id
                              ? "bg-ink-50 text-ink-950 font-medium"
                              : "bg-white/5 text-ink-300 hover:bg-white/10",
                          )}
                        >
                          {p.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              <button
                type="button"
                onClick={handleSubmit}
                disabled={isPending}
                className="w-full h-14 rounded-md bg-accent-500 hover:bg-accent-400 disabled:bg-ink-700 disabled:text-ink-500 text-ink-950 font-medium transition-all duration-base shadow-brand"
              >
                {isPending ? "Считаем…" : "Рассчитать подбор"}
              </button>
            </div>

            {/* Right: live preview */}
            <div className="lg:col-span-7 lg:border-l lg:border-white/[0.06] lg:pl-12 relative">
              {helperOpen ? (
                <div className="bg-white rounded-card p-6 max-h-[600px] overflow-y-auto">
                  <QHelper
                    onCalculate={(Q) => {
                      setQValue(Q.toFixed(1));
                      setQUnit("m3h");
                      setHelperOpen(false);
                    }}
                  />
                </div>
              ) : isPending ? (
                <PreviewSkeleton />
              ) : result ? (
                <PreviewResult result={result} wastewater={wastewater} />
              ) : (
                <PreviewEmpty />
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function PreviewEmpty() {
  return (
    <div className="h-full min-h-[300px] flex items-center justify-center">
      <div className="text-center max-w-sm">
        <div className="text-[10px] font-mono uppercase tracking-wider text-ink-500 mb-2">
          Превью результата
        </div>
        <p className="text-ink-400 text-sm leading-relaxed">
          Введите расход Q и нажмите «Рассчитать» — здесь появится рекомендованный насос с
          диапазоном цены и спецификацией.
        </p>
      </div>
    </div>
  );
}

function PreviewSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-12 w-32 bg-white/10 rounded" />
      <div className="h-20 bg-white/5 rounded-md" />
      <div className="h-32 bg-white/5 rounded-md" />
    </div>
  );
}

function PreviewResult({
  result,
  wastewater,
}: {
  result: SelectionResult;
  wastewater: WastewaterType;
}) {
  const recommended = result.results.mid ?? result.results.budget ?? result.results.premium;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-ink-400 mb-1">
            Q расчётный
          </div>
          <div className="font-mono tabular-nums text-3xl md:text-5xl text-ink-50">
            {(result.computed?.H_full_m
              ? result.computed.H_full_m.toFixed(1)
              : "–")}
            <span className="ml-2 text-base text-ink-400">м³/ч</span>
          </div>
        </div>
        <div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-ink-400 mb-1">
            H расчётный
          </div>
          <div className="font-mono tabular-nums text-3xl md:text-5xl text-ink-50">
            {result.computed?.H_full_m?.toFixed(1) ?? "–"}
            <span className="ml-2 text-base text-ink-400">м</span>
          </div>
        </div>
      </div>

      {recommended && (
        <div className="bg-ink-50 rounded-card p-5 relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-accent-500" />
          <div className="text-[10px] font-mono uppercase tracking-wider text-accent-600 mb-1">
            Рекомендуем для {wastewaterTypeLabels[wastewater].toLowerCase()}
          </div>
          <div className="font-display text-xl font-semibold text-ink-950">
            {recommended.brand} {recommended.model}
          </div>
          <div className="text-sm text-ink-600 mt-1">
            {recommended.P_kW} кВт ·{" "}
            {recommended.discharge_DN_mm ? `DN${recommended.discharge_DN_mm}` : "–"} ·{" "}
            {recommended.impeller}
          </div>
        </div>
      )}

      <p className="text-sm text-ink-400 italic">
        Прокрутите ниже — полное сравнение бюджет / средний / премиум сегментов.
      </p>
    </div>
  );
}
