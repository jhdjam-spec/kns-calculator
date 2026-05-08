"use client";

import { useState } from "react";
import { ArrowRight, FileDown, ShieldCheck, Building2, MapPin } from "lucide-react";
import { QHCurve } from "./QHCurve";

interface HeroProps {
  onCalculate: (Q_m3h: number) => void;
  isCalculating?: boolean;
}

/**
 * Скачивание пустого опросного листа DOCX через POST /handoff/empty-questionnaire-docx.
 * Один и тот же файл с двумя названиями:
 * — «Техзадание_КНС.docx» — для заказчика, формулировка через «техническое задание»
 * — «Опросный_лист_КНС.docx» — для инженера, формулировка через «опросный лист»
 */
async function downloadEmptyQuestionnaire(filename: string): Promise<void> {
  const res = await fetch("/api/backend/handoff/empty-questionnaire-docx", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    alert(`Не удалось скачать форму: ${res.status} ${res.statusText}`);
    return;
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function Hero({ onCalculate, isCalculating }: HeroProps) {
  const [qInput, setQInput] = useState("21.2");

  const qNumeric = parseFloat(qInput);
  // Нормируем Q в 0..1 для позиционирования точки на графике (диапазон 0..200 м³/ч)
  const qNormalized = Math.min(Math.max(qNumeric / 200, 0.1), 0.95);

  return (
    <section
      id="hero"
      className="relative overflow-hidden bg-ink-950 pt-32 pb-24 md:pt-40 md:pb-32"
    >
      {/* Background: radial gradient + isometric grid + noise */}
      <div
        className="absolute inset-0 opacity-60"
        style={{
          background:
            "radial-gradient(ellipse 1200px 600px at 18% 30%, rgba(30, 58, 95, 0.55), transparent 70%)",
        }}
      />
      <div
        className="absolute inset-0 opacity-100"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)
          `,
          backgroundSize: "32px 32px",
          maskImage: "radial-gradient(ellipse at center, black 30%, transparent 80%)",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 30%, transparent 80%)",
        }}
      />

      <div className="relative max-w-7xl mx-auto px-5 md:px-10 grid lg:grid-cols-12 gap-10 lg:gap-16 items-center">
        {/* Left: H1 + form */}
        <div className="lg:col-span-7 space-y-8">
          <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-ink-300">
            <span className="block w-6 h-px bg-accent-500" />
            КАЛЬКУЛЯТОР · 2026
          </div>

          <h1 className="font-display text-4xl md:text-5xl lg:text-7xl font-bold text-ink-50 leading-[1.05] tracking-tightest">
            Подбор насоса
            <br />
            для <span className="font-normal italic text-accent-500">КНС, ЛОС и СПД</span>
            <br />
            за 60 секунд
          </h1>

          <p className="text-sm md:text-base text-ink-500 leading-relaxed max-w-xl -mt-2">
            <span className="text-ink-400">КНС</span> — канализационные насосные станции ·{" "}
            <span className="text-ink-400">ЛОС</span> — локальные очистные сооружения ·{" "}
            <span className="text-ink-400">СПД</span> — станции повышения давления
          </p>

          <p className="text-lg md:text-xl text-ink-300 leading-relaxed max-w-xl">
            От ТЗ до спецификации с гидравликой по СП 32.13330. Без регистрации.
            От производителя оборудования с 2009 года.
          </p>

          {/* One-field calc */}
          <div className="flex flex-col sm:flex-row gap-3 max-w-lg">
            <div className="flex-1 group relative">
              <label
                htmlFor="hero-q"
                className="absolute left-4 top-1.5 text-[10px] font-mono uppercase tracking-wider text-ink-400"
              >
                Расход Q, м³/ч
              </label>
              <input
                id="hero-q"
                type="number"
                inputMode="decimal"
                value={qInput}
                onChange={(e) => setQInput(e.target.value)}
                step="0.1"
                min="0"
                className="w-full h-16 px-4 pt-7 pb-2 rounded-md bg-white/5 border border-white/10 text-ink-50 font-mono text-xl tabular-nums focus:border-accent-500 focus:bg-white/10 outline-none transition-colors duration-base"
              />
            </div>
            <button
              type="button"
              disabled={isCalculating || !qNumeric || qNumeric <= 0}
              onClick={() => onCalculate(qNumeric)}
              className="group h-16 px-6 rounded-md bg-accent-500 hover:bg-accent-400 disabled:bg-ink-700 disabled:text-ink-500 text-ink-950 font-medium inline-flex items-center justify-center gap-2 transition-all duration-base shadow-brand"
            >
              {isCalculating ? "Считаем…" : "Рассчитать"}
              <ArrowRight
                size={18}
                strokeWidth={2}
                className="transition-transform duration-base group-hover:translate-x-1"
              />
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-ink-400">
            <span className="inline-flex items-center gap-1.5">
              <ShieldCheck size={14} strokeWidth={1.5} className="text-accent-500" />
              Без регистрации
            </span>
            <span className="text-ink-700">·</span>
            <span className="inline-flex items-center gap-1.5">
              <Building2 size={14} strokeWidth={1.5} className="text-accent-500" />
              284 модели в базе
            </span>
            <span className="text-ink-700">·</span>
            <span className="inline-flex items-center gap-1.5">
              <MapPin size={14} strokeWidth={1.5} className="text-accent-500" />
              Производство в Адыгее
            </span>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-5">
            <button
              type="button"
              onClick={() => downloadEmptyQuestionnaire("Техзадание_КНС.docx")}
              className="inline-flex items-center gap-2 text-sm text-ink-300 hover:text-accent-500 transition-colors group"
            >
              <FileDown size={16} strokeWidth={1.5} />
              Скачать техзадание DOCX
              <ArrowRight
                size={14}
                strokeWidth={2}
                className="opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-base"
              />
            </button>
            <span className="hidden sm:inline text-ink-700">·</span>
            <button
              type="button"
              onClick={() => downloadEmptyQuestionnaire("Опросный_лист_КНС.docx")}
              className="inline-flex items-center gap-2 text-sm text-ink-300 hover:text-accent-500 transition-colors group"
            >
              <FileDown size={16} strokeWidth={1.5} />
              Скачать опросный лист DOCX
              <ArrowRight
                size={14}
                strokeWidth={2}
                className="opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-base"
              />
            </button>
          </div>
        </div>

        {/* Right: Q-H curve */}
        <div className="lg:col-span-5 hidden lg:block">
          <div className="relative aspect-[4/3] rounded-block bg-white/[0.02] border border-white/[0.06] p-4 backdrop-blur-sm">
            <QHCurve qNormalized={qNormalized} />
          </div>
        </div>
      </div>
    </section>
  );
}
