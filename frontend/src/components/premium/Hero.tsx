"use client";

import { useState } from "react";
import { ArrowRight, FileDown, ShieldCheck, Building2, MapPin } from "lucide-react";
import { QHCurve } from "./QHCurve";
import { useMode } from "@/components/providers/ModeProvider";

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
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api/backend";

async function downloadEmptyQuestionnaire(filename: string): Promise<void> {
  const res = await fetch(`${API_BASE}/handoff/empty-questionnaire-docx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    throw new Error(`Не удалось скачать форму (${res.status})`);
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
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const { mode } = useMode();

  // Mode-aware CTA. Менеджер видит обещание (срок, простота),
  // инженер — инструмент («гидравлический расчёт»).
  const heroCtaText = isCalculating
    ? "Считаем…"
    : mode === "engineer"
      ? "Запустить гидравлический расчёт"
      : "Подобрать насос — 60 сек";
  const qLabel = mode === "engineer" ? "Q, м³/ч" : "Расход (м³/час)";

  const handleDownload = async (filename: string) => {
    setDownloadError(null);
    try {
      await downloadEmptyQuestionnaire(filename);
    } catch (e) {
      setDownloadError(
        e instanceof Error
          ? e.message
          : "Не удалось скачать форму. Попробуйте позже.",
      );
    }
  };

  const qNumeric = parseFloat(qInput);
  // Нормируем Q в 0..1 для позиционирования точки на графике (диапазон 0..200 м³/ч)
  const qNormalized = Math.min(Math.max(qNumeric / 200, 0.1), 0.95);

  return (
    <section
      id="hero"
      className="relative overflow-hidden bg-ink-50 dark:bg-ink-950 pt-16 pb-20 sm:pt-20 md:pt-28 md:pb-32 transition-colors duration-base"
    >
      {/* Background: radial gradient — light & dark variants */}
      {/* Light: subtle deep teal-blue tint on cream */}
      <div
        className="absolute inset-0 opacity-70 dark:hidden"
        style={{
          background:
            "radial-gradient(ellipse 1200px 600px at 18% 30%, rgba(44, 111, 130, 0.10), transparent 70%)",
        }}
      />
      {/* Dark: original deep brand radial */}
      <div
        className="absolute inset-0 opacity-60 hidden dark:block"
        style={{
          background:
            "radial-gradient(ellipse 1200px 600px at 18% 30%, rgba(30, 58, 95, 0.55), transparent 70%)",
        }}
      />

      {/* Isometric grid — light variant (dark ink lines on cream) */}
      <div
        className="absolute inset-0 opacity-100 dark:hidden"
        style={{
          backgroundImage: `
            linear-gradient(rgba(20,20,18,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(20,20,18,0.04) 1px, transparent 1px)
          `,
          backgroundSize: "32px 32px",
          maskImage: "radial-gradient(ellipse at center, black 30%, transparent 80%)",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 30%, transparent 80%)",
        }}
      />
      {/* Isometric grid — dark variant (subtle white lines) */}
      <div
        className="absolute inset-0 opacity-100 hidden dark:block"
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
          <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-ink-600 dark:text-ink-300">
            <span className="block w-6 h-px bg-brand-600 dark:bg-accent-500" />
            КАЛЬКУЛЯТОР · 2026
          </div>

          <h1 className="font-display text-[2rem] sm:text-4xl md:text-5xl lg:text-7xl font-bold text-ink-900 dark:text-ink-50 leading-[1.05] tracking-tightest">
            Подбор насоса
            <br />
            для{" "}
            <span className="font-normal italic text-brand-700 dark:text-accent-500">
              КНС, ЛОС и СПД
            </span>
            <br />
            за минуту
          </h1>

          <p className="text-sm md:text-base text-ink-600 dark:text-ink-500 leading-relaxed max-w-xl -mt-2">
            <span className="text-ink-700 dark:text-ink-400">КНС</span> — канализационные насосные станции ·{" "}
            <span className="text-ink-700 dark:text-ink-400">ЛОС</span> — локальные очистные сооружения ·{" "}
            <span className="text-ink-700 dark:text-ink-400">СПД</span> — станции повышения давления
          </p>

          <p className="text-lg md:text-xl text-ink-700 dark:text-ink-300 leading-relaxed max-w-xl">
            От ТЗ до спецификации с гидравликой по СП 32.13330. Без регистрации.
            От производителя оборудования с 2009 года.
          </p>

          {/* One-field calc */}
          <div className="flex flex-col sm:flex-row gap-3 max-w-lg">
            <div className="flex-1 group relative">
              <label
                htmlFor="hero-q"
                className="absolute left-4 top-1.5 text-[10px] font-mono uppercase tracking-wider text-ink-500 dark:text-ink-400"
                title={
                  mode === "engineer"
                    ? "Q — расход, формула Q = V/t (СП 32.13330 §6.2)"
                    : "Сколько воды в час нужно перекачивать"
                }
              >
                {qLabel}
              </label>
              <input
                id="hero-q"
                type="number"
                inputMode="decimal"
                value={qInput}
                onChange={(e) => setQInput(e.target.value)}
                step="0.1"
                min="0"
                className="w-full h-14 sm:h-16 px-4 pt-6 sm:pt-7 pb-2 rounded-md bg-white border border-ink-300 text-ink-900 shadow-premium-sm dark:bg-white/5 dark:border-white/10 dark:text-ink-50 dark:shadow-none font-mono text-base sm:text-xl tabular-nums focus:border-brand-600 focus:bg-white dark:focus:border-accent-500 dark:focus:bg-white/10 outline-none transition-colors duration-base"
              />
            </div>
            <button
              type="button"
              disabled={isCalculating || !qNumeric || qNumeric <= 0}
              onClick={() => onCalculate(qNumeric)}
              className="group h-14 sm:h-16 px-6 rounded-md bg-brand-600 hover:bg-brand-700 text-ink-50 dark:bg-accent-500 dark:hover:bg-accent-400 dark:text-ink-950 disabled:bg-ink-300 disabled:text-ink-500 dark:disabled:bg-ink-700 dark:disabled:text-ink-500 font-medium inline-flex items-center justify-center gap-2 transition-all duration-base shadow-brand"
            >
              {heroCtaText}
              <ArrowRight
                size={18}
                strokeWidth={2}
                className="transition-transform duration-base group-hover:translate-x-1"
              />
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-ink-600 dark:text-ink-400">
            <span className="inline-flex items-center gap-1.5">
              <ShieldCheck size={14} strokeWidth={1.5} className="text-brand-600 dark:text-accent-500" />
              Без регистрации
            </span>
            <span className="text-ink-300 dark:text-ink-700">·</span>
            <span className="inline-flex items-center gap-1.5">
              <Building2 size={14} strokeWidth={1.5} className="text-brand-600 dark:text-accent-500" />
              284 модели в базе
            </span>
            <span className="text-ink-300 dark:text-ink-700">·</span>
            <span className="inline-flex items-center gap-1.5">
              <MapPin size={14} strokeWidth={1.5} className="text-brand-600 dark:text-accent-500" />
              Производство в Адыгее
            </span>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-5">
            <button
              type="button"
              onClick={() => handleDownload("Техзадание_КНС.docx")}
              className="inline-flex items-center gap-2 text-sm text-ink-700 hover:text-brand-700 dark:text-ink-300 dark:hover:text-accent-500 transition-colors group"
            >
              <FileDown size={16} strokeWidth={1.5} />
              Скачать техзадание DOCX
              <ArrowRight
                size={14}
                strokeWidth={2}
                className="opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-base"
              />
            </button>
            <span className="hidden sm:inline text-ink-300 dark:text-ink-700">·</span>
            <button
              type="button"
              onClick={() => handleDownload("Опросный_лист_КНС.docx")}
              className="inline-flex items-center gap-2 text-sm text-ink-700 hover:text-brand-700 dark:text-ink-300 dark:hover:text-accent-500 transition-colors group"
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

          {downloadError && (
            <div
              role="alert"
              className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-300 max-w-xl"
            >
              {downloadError}
            </div>
          )}
        </div>

        {/* Right: Q-H curve */}
        <div className="lg:col-span-5 hidden lg:block">
          <div className="relative aspect-[4/3] rounded-block bg-white/70 border border-ink-200 shadow-premium-sm dark:bg-white/[0.02] dark:border-white/[0.06] dark:shadow-none p-4 backdrop-blur-sm">
            <QHCurve qNormalized={qNormalized} />
          </div>
        </div>
      </div>
    </section>
  );
}
