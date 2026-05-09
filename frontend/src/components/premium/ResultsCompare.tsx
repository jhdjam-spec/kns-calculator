"use client";

import { useState } from "react";
import clsx from "clsx";
import { Check, ChevronDown, AlertTriangle } from "lucide-react";
import type { SelectionResult, PumpResult, PriceBreakdown } from "@/schemas/result";
import { triggerReasonLabels } from "@/schemas/result";
import { formatRubFull, calcMatchPct } from "@/lib/units";

interface ResultsCompareProps {
  result: SelectionResult;
}

const segmentMeta = {
  budget: { label: "БЮДЖЕТ", className: "border-ink-300", textClass: "text-ink-600" },
  mid: { label: "РЕКОМЕНДУЕМ", className: "border-accent-500", textClass: "text-accent-600" },
  premium: { label: "ПРЕМИУМ", className: "border-brand-700", textClass: "text-brand-700" },
} as const;

export function ResultsCompare({ result }: ResultsCompareProps) {
  const segments = ["budget", "mid", "premium"] as const;

  return (
    <section id="results" className="py-20 md:py-24 bg-ink-50 border-t border-ink-200">
      <div className="max-w-7xl mx-auto px-5 md:px-10">
        <div className="mb-12 max-w-2xl">
          <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-ink-500 mb-4">
            <span className="block w-6 h-px bg-accent-500" />
            РЕЗУЛЬТАТ
          </div>
          <h2 className="font-display text-3xl md:text-4xl font-semibold text-ink-950 leading-tight tracking-tight">
            Топ-3 насоса в трёх сегментах
          </h2>
          {result.summary_text && (
            <p className="mt-3 text-ink-600">{result.summary_text}</p>
          )}
        </div>

        {result.engineer_handoff_required && (
          <HandoffBanner reasons={result.trigger_reasons} />
        )}

        <div className="grid md:grid-cols-3 gap-4 md:gap-6">
          {segments.map((seg) => {
            const pump = result.results[seg];
            const isHighlighted = seg === "mid";

            if (!pump) {
              return (
                <div
                  key={seg}
                  className="rounded-card border border-dashed border-ink-300 p-6 bg-ink-100/50 flex items-center justify-center min-h-[280px]"
                >
                  <div className="text-center">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-ink-500 mb-2">
                      {segmentMeta[seg].label}
                    </div>
                    <p className="text-ink-500 text-sm">
                      Нет подходящих моделей в этом сегменте
                    </p>
                  </div>
                </div>
              );
            }

            return (
              <PumpCard
                key={seg}
                pump={pump}
                segment={seg}
                isHighlighted={isHighlighted}
                Q_m3h={pump.duty_point?.Q_m3h ?? 0}
                H_m={pump.duty_point?.H_m ?? 0}
              />
            );
          })}
        </div>

        {result.assumptions && result.assumptions.length > 0 && (
          <div className="mt-8 p-4 rounded-card bg-ink-100 border border-ink-200">
            <div className="text-xs font-mono uppercase tracking-wider text-ink-500 mb-2">
              Использованы дефолты
            </div>
            <ul className="text-sm text-ink-700 space-y-1">
              {result.assumptions.map((a, i) => (
                <li key={i}>· {a}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

function PumpCard({
  pump,
  segment,
  isHighlighted,
  Q_m3h,
  H_m,
}: {
  pump: PumpResult;
  segment: "budget" | "mid" | "premium";
  isHighlighted: boolean;
  Q_m3h: number;
  H_m: number;
}) {
  const [expanded, setExpanded] = useState(isHighlighted);
  const meta = segmentMeta[segment];
  const matchPct = calcMatchPct(
    Q_m3h,
    H_m,
    pump.envelope.Q_BEP_m3h ?? null,
    pump.envelope.H_BEP_m ?? null,
    pump.envelope,
  );

  const breakdown = pump.price_breakdown;
  const lowPrice = breakdown.total_low_rub || pump.price_estimate_rub * 0.9;
  const highPrice = breakdown.total_high_rub || pump.price_estimate_rub * 1.1;

  return (
    <div
      className={clsx(
        "relative rounded-card bg-white border-t-2 p-6 md:p-8 transition-all duration-base hover:shadow-premium-md",
        meta.className,
        isHighlighted && "md:scale-[1.02] shadow-premium-lg ring-1 ring-accent-500/20",
      )}
    >
      <div className="flex items-center justify-between mb-4">
        <span
          className={clsx(
            "text-[10px] font-mono uppercase tracking-widest font-medium",
            meta.textClass,
          )}
        >
          {meta.label}
        </span>
        <MatchRing pct={matchPct} highlight={isHighlighted} />
      </div>

      <div className="font-display text-xl font-semibold text-ink-950 leading-tight">
        {pump.brand}
      </div>
      <div className="text-base text-ink-700 mt-0.5">{pump.model}</div>

      <div className="mt-4 grid grid-cols-3 gap-2 text-xs font-mono text-ink-500">
        <div title="Мощность электродвигателя">
          <div className="uppercase tracking-wider text-[9px]">P, мощн.</div>
          <div className="text-ink-950 text-sm tabular-nums">{pump.P_kW} кВт</div>
        </div>
        <div title="Диаметр напорного патрубка (Diameter Nominal)">
          <div className="uppercase tracking-wider text-[9px]">DN, патруб.</div>
          <div className="text-ink-950 text-sm tabular-nums">
            {pump.discharge_DN_mm ? `${pump.discharge_DN_mm} мм` : "–"}
          </div>
        </div>
        <div title="Тип рабочего колеса (impeller). Vortex — открытое для волокон, channel — каналное, cutter — с режущим механизмом">
          <div className="uppercase tracking-wider text-[9px]">Тип к/к</div>
          <div className="text-ink-950 text-sm">{pump.impeller || "–"}</div>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-ink-200">
        <div className="text-[10px] font-mono uppercase tracking-wider text-ink-500 mb-1">
          Комплект, ориентир
        </div>
        <div className="font-display text-2xl md:text-3xl font-semibold text-ink-950 tabular-nums">
          {formatRubFull(pump.price_estimate_rub)}
        </div>
        <div className="text-xs font-mono text-ink-500 tabular-nums mt-1">
          {formatRubFull(lowPrice)} — {formatRubFull(highPrice)}
        </div>
      </div>

      {breakdown && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="mt-4 inline-flex items-center gap-1.5 text-xs font-medium text-brand-700 hover:text-brand-600 transition-colors"
        >
          <ChevronDown
            size={14}
            strokeWidth={2}
            className={clsx("transition-transform duration-base", expanded && "rotate-180")}
          />
          {expanded ? "Скрыть состав" : "Что входит в комплект"}
        </button>
      )}

      {expanded && breakdown && <BomTable breakdown={breakdown} />}
    </div>
  );
}

function MatchRing({ pct, highlight }: { pct: number; highlight: boolean }) {
  const r = 16;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - pct / 100);
  return (
    <div className="relative size-10">
      <svg className="size-10 -rotate-90" viewBox="0 0 40 40">
        <circle
          cx="20"
          cy="20"
          r={r}
          fill="none"
          stroke="rgb(232 232 229)"
          strokeWidth="3"
        />
        <circle
          cx="20"
          cy="20"
          r={r}
          fill="none"
          stroke={highlight ? "rgb(201 162 74)" : "rgb(24 69 85)"}
          strokeWidth="3"
          strokeDasharray={c}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 600ms cubic-bezier(0.16, 1, 0.3, 1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-[10px] font-mono font-medium text-ink-950 tabular-nums">
        {pct}
      </div>
    </div>
  );
}

function BomTable({ breakdown }: { breakdown: PriceBreakdown }) {
  const items: { label: string; rub: number; hint?: string }[] = [
    { label: "Насос(ы)", rub: breakdown.pump_rub, hint: "1 рабочий + 1 резервный по СП 32 §6.2" },
    { label: "Корпус", rub: breakdown.corpus_rub, hint: "Полимерный (стеклопластик / ПЭ)" },
    { label: "Автомуфта (АТМ)", rub: breakdown.atm_rub, hint: "Автоматическое сцепление насоса с напорным трубопроводом" },
    { label: "Задвижка", rub: breakdown.valve_rub },
    { label: "Обратный клапан", rub: breakdown.check_valve_rub, hint: "Предотвращает обратный ток жидкости при остановке насоса" },
    { label: "Направляющие", rub: breakdown.rails_rub, hint: "Трубы для опускания/подъёма насоса (AISI 304)" },
    { label: "Цепь подъёма", rub: breakdown.chain_rub },
    { label: "Поплавки (датчики уровня)", rub: breakdown.floats_rub, hint: "Датчики уровня для пуска/останова насоса" },
    { label: "Шкаф управления", rub: breakdown.cabinet_rub, hint: "ШУ с пускателями и автоматами защиты" },
  ].filter((i) => i.rub > 0);

  return (
    <div className="mt-4 pt-4 border-t border-ink-200 space-y-1.5">
      {items.map((item) => (
        <div
          key={item.label}
          className="flex justify-between text-sm"
          title={item.hint}
        >
          <span className="text-ink-600">{item.label}</span>
          <span className="font-mono tabular-nums text-ink-950">
            {formatRubFull(item.rub)}
          </span>
        </div>
      ))}
      <div className="pt-2 mt-2 border-t border-ink-200 flex justify-between">
        <span className="text-sm font-medium text-ink-950">Итого с НДС</span>
        <span className="font-mono tabular-nums font-semibold text-ink-950">
          {formatRubFull(breakdown.total_rub)}
        </span>
      </div>
    </div>
  );
}

function HandoffBanner({ reasons }: { reasons: string[] }) {
  return (
    <div className="mb-8 rounded-card bg-accent-500/10 border border-accent-500/30 p-5 flex items-start gap-3">
      <AlertTriangle
        size={20}
        strokeWidth={1.75}
        className="text-accent-600 shrink-0 mt-0.5"
      />
      <div>
        <div className="font-display font-semibold text-ink-950 mb-1">
          Требуется уточнение инженером
        </div>
        <p className="text-sm text-ink-700 mb-2">
          Расчёт корректен, но параметры объекта требуют дополнительной проверки специалистом
          перед заказом.
        </p>
        <ul className="text-sm text-ink-700 space-y-0.5">
          {reasons.map((r) => (
            <li key={r} className="flex items-start gap-2">
              <Check size={14} strokeWidth={2} className="text-accent-600 shrink-0 mt-1" />
              {triggerReasonLabels[r] || r}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
