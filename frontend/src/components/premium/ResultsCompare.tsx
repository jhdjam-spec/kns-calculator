"use client";

import { useState } from "react";
import clsx from "clsx";
import { Check, ChevronDown, AlertTriangle, FileDown, FileSpreadsheet } from "lucide-react";
import type { SelectionResult, PumpResult, PriceBreakdown } from "@/schemas/result";
import { triggerReasonLabels } from "@/schemas/result";
import { formatRubFull, calcMatchPct } from "@/lib/units";
import { openEncyclopediaDrawer } from "@/components/teach/EncyclopediaDrawer";
import {
  downloadCalculationPdf,
  downloadBomCsv,
  type BOMItem,
} from "@/lib/api-extended";

/** Скачивание Blob через временный <a download>. */
function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Сборка BOM из результата быстрого подбора (упрощённо — на основе price_breakdown). */
function buildBomFromQuickResult(pump: PumpResult): BOMItem[] {
  const b = pump.price_breakdown;
  if (!b) return [];
  const items: BOMItem[] = [];
  if (b.pump_rub > 0) items.push({
    section: "pumps",
    name: `${pump.brand} ${pump.model}`,
    article: pump.id || "",
    manufacturer: pump.brand,
    quantity: 2,
    units: "шт",
    price_rub_2026: b.pump_rub / 2,
    note: "1 рабочий + 1 резервный (СП 32 §6.2)",
  });
  if (b.corpus_rub > 0) items.push({
    section: "corpus", name: "Корпус КНС", quantity: 1, units: "шт",
    price_rub_2026: b.corpus_rub,
  });
  if (b.atm_rub > 0) items.push({
    section: "piping", name: "Автомуфта (АТМ)", quantity: 2, units: "шт",
    price_rub_2026: b.atm_rub / 2,
  });
  if (b.valve_rub > 0) items.push({
    section: "piping", name: "Задвижка", quantity: 2, units: "шт",
    price_rub_2026: b.valve_rub / 2,
  });
  if (b.check_valve_rub > 0) items.push({
    section: "piping", name: "Обратный клапан", quantity: 2, units: "шт",
    price_rub_2026: b.check_valve_rub / 2,
  });
  if (b.rails_rub > 0) items.push({
    section: "piping", name: "Направляющие AISI 304", quantity: 1, units: "комплект",
    price_rub_2026: b.rails_rub,
  });
  if (b.chain_rub > 0) items.push({
    section: "piping", name: "Цепь подъёма", quantity: 1, units: "комплект",
    price_rub_2026: b.chain_rub,
  });
  if (b.floats_rub > 0) items.push({
    section: "automation", name: "Поплавки (датчики уровня)", quantity: 4, units: "шт",
    price_rub_2026: b.floats_rub / 4,
  });
  if (b.cabinet_rub > 0) items.push({
    section: "control_panel", name: "Шкаф управления", quantity: 1, units: "шт",
    price_rub_2026: b.cabinet_rub,
  });
  return items;
}

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

        {/* Кнопки экспорта по выбранному (рекомендуемому) насосу */}
        {result.results.mid && <ExportActions pump={result.results.mid} />}

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

/** Полоска действий: скачать PDF/CSV для выбранного насоса. */
function ExportActions({ pump }: { pump: PumpResult }) {
  const [pdfStatus, setPdfStatus] = useState<"idle" | "loading" | "error">("idle");
  const [csvStatus, setCsvStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const filenameSuffix = `${pump.brand}_${pump.model}`.replace(/[^a-zA-Z0-9_-]/g, "_");

  const handlePdf = async () => {
    setPdfStatus("loading");
    setError(null);
    try {
      const bomItems = buildBomFromQuickResult(pump);
      const blob = await downloadCalculationPdf({
        project_name: `Подбор насоса — ${pump.brand} ${pump.model}`,
        inputs_summary: {
          "Расход Q, м³/ч": pump.duty_point?.Q_m3h ?? "—",
          "Напор H, м": pump.duty_point?.H_m ?? "—",
        },
        hydraulics: {
          Q_m3h: pump.duty_point?.Q_m3h,
          H_m: pump.duty_point?.H_m,
          "P, кВт": pump.P_kW,
          "DN, мм": pump.discharge_DN_mm,
          "Тип рабочего колеса": pump.impeller,
        },
        bom: bomItems.map((it) => ({
          name: it.name,
          article: it.article || "",
          quantity: it.quantity ?? 1,
          price_rub: it.price_rub_2026 ?? 0,
        })),
        references: [
          {
            regulation_code: "СП 32.13330.2018",
            section: "§6.2",
            purpose: "Канализация наружная — расчёт КНС",
          },
        ],
      });
      triggerBlobDownload(blob, `Отчёт_${filenameSuffix}.pdf`);
      setPdfStatus("idle");
    } catch (e) {
      setPdfStatus("error");
      setError(String(e));
    }
  };

  const handleCsv = async () => {
    setCsvStatus("loading");
    setError(null);
    try {
      const items = buildBomFromQuickResult(pump);
      const blob = await downloadBomCsv({
        project_name: `${pump.brand} ${pump.model}`,
        items,
      });
      triggerBlobDownload(blob, `BOM_${filenameSuffix}.csv`);
      setCsvStatus("idle");
    } catch (e) {
      setCsvStatus("error");
      setError(String(e));
    }
  };

  return (
    <div className="mt-8 p-5 rounded-card bg-white border border-ink-200">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="text-xs font-mono uppercase tracking-wider text-ink-500 mb-1">
            Скачать по выбранному насосу
          </div>
          <div className="text-sm text-ink-700">
            <strong>{pump.brand} {pump.model}</strong> — отчёт и спецификация для тендера или КП
          </div>
        </div>
        <div className="flex flex-col sm:flex-row gap-2">
          <button
            type="button"
            onClick={handlePdf}
            disabled={pdfStatus === "loading"}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-ink-950 text-ink-50 text-sm font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            <FileDown size={16} strokeWidth={1.75} />
            {pdfStatus === "loading" ? "Генерация…" : "Расчётная записка (PDF)"}
          </button>
          <button
            type="button"
            onClick={handleCsv}
            disabled={csvStatus === "loading"}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-ink-100 text-ink-950 text-sm font-medium hover:bg-ink-200 disabled:opacity-50 transition-colors border border-ink-300"
          >
            <FileSpreadsheet size={16} strokeWidth={1.75} />
            {csvStatus === "loading" ? "Сборка…" : "BOM — список оборудования (CSV)"}
          </button>
        </div>
      </div>
      {error && (
        <div className="mt-3 p-2 rounded bg-red-50 border border-red-200 text-xs text-red-700">
          Ошибка экспорта: {error}
        </div>
      )}
    </div>
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
        <button
          type="button"
          onClick={() =>
            openEncyclopediaDrawer({
              topic: "electrical",
              anchor: "Двигатели насосов",
              valueLabel: `Мощность ${pump.P_kW} кВт`,
            })
          }
          title="Мощность электродвигателя — кликните для справки"
          className="text-left hover:bg-ink-100 rounded p-1 -m-1 transition-colors"
        >
          <div className="uppercase tracking-wider text-[9px]">P, мощн.</div>
          <div className="text-ink-950 text-sm tabular-nums">{pump.P_kW} кВт</div>
        </button>
        <button
          type="button"
          onClick={() =>
            openEncyclopediaDrawer({
              topic: "hydraulics",
              anchor: "Гидравлические сопротивления",
              valueLabel: `DN${pump.discharge_DN_mm} напорный патрубок`,
            })
          }
          title="Диаметр напорного патрубка (Diameter Nominal)"
          className="text-left hover:bg-ink-100 rounded p-1 -m-1 transition-colors"
        >
          <div className="uppercase tracking-wider text-[9px]">DN, патруб.</div>
          <div className="text-ink-950 text-sm tabular-nums">
            {pump.discharge_DN_mm ? `${pump.discharge_DN_mm} мм` : "–"}
          </div>
        </button>
        <button
          type="button"
          onClick={() =>
            openEncyclopediaDrawer({
              topic: "hydraulics",
              anchor: "Q-H насосов",
              valueLabel: `Рабочее колесо: ${pump.impeller || "—"}`,
            })
          }
          title="Тип рабочего колеса. Vortex — открытое для волокон, channel — канальное, cutter — с режущим механизмом"
          className="text-left hover:bg-ink-100 rounded p-1 -m-1 transition-colors"
        >
          <div className="uppercase tracking-wider text-[9px]">Тип к/к</div>
          <div className="text-ink-950 text-sm">{pump.impeller || "–"}</div>
        </button>
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
          // SVG stroke-dashoffset не покрывается Tailwind transition утилитами
          // eslint-disable-next-line react/forbid-dom-props
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
  const items: {
    label: string;
    rub: number;
    hint?: string;
    drawer?: { topic: string; anchor: string };
  }[] = [
    {
      label: "Насос(ы)",
      rub: breakdown.pump_rub,
      hint: "1 рабочий + 1 резервный по СП 32 §6.2",
      drawer: { topic: "hydraulics", anchor: "Q-H насосов" },
    },
    {
      label: "Корпус",
      rub: breakdown.corpus_rub,
      hint: "Полимерный (стеклопластик / ПЭ)",
      drawer: { topic: "structural", anchor: "Корпус КНС" },
    },
    {
      label: "Автомуфта (АТМ)",
      rub: breakdown.atm_rub,
      hint: "Автоматическое сцепление насоса с напорным трубопроводом",
    },
    { label: "Задвижка", rub: breakdown.valve_rub },
    {
      label: "Обратный клапан",
      rub: breakdown.check_valve_rub,
      hint: "Предотвращает обратный ток жидкости при остановке насоса",
      drawer: { topic: "hydraulics", anchor: "Гидроудар" },
    },
    {
      label: "Направляющие",
      rub: breakdown.rails_rub,
      hint: "Трубы для опускания/подъёма насоса (AISI 304)",
    },
    { label: "Цепь подъёма", rub: breakdown.chain_rub },
    {
      label: "Поплавки (датчики уровня)",
      rub: breakdown.floats_rub,
      hint: "Датчики уровня для пуска/останова насоса",
      drawer: { topic: "electrical", anchor: "Логика управления" },
    },
    {
      label: "Шкаф управления",
      rub: breakdown.cabinet_rub,
      hint: "ШУ с пускателями и автоматами защиты",
      drawer: { topic: "electrical", anchor: "Шкафы НКУ" },
    },
  ].filter((i) => i.rub > 0);

  return (
    <div className="mt-4 pt-4 border-t border-ink-200 space-y-1.5">
      {items.map((item) =>
        item.drawer ? (
          <button
            key={item.label}
            type="button"
            onClick={() =>
              openEncyclopediaDrawer({
                topic: item.drawer!.topic,
                anchor: item.drawer!.anchor,
                valueLabel: item.label,
              })
            }
            title={item.hint || "Открыть справку"}
            className="w-full flex justify-between items-center text-sm hover:bg-ink-100 rounded px-1 -mx-1 py-0.5 transition-colors"
          >
            <span className="text-ink-600 underline decoration-dotted decoration-accent-500/40 underline-offset-2">
              {item.label}
            </span>
            <span className="font-mono tabular-nums text-ink-950">
              {formatRubFull(item.rub)}
            </span>
          </button>
        ) : (
          <div
            key={item.label}
            className="flex justify-between text-sm px-1 -mx-1"
            title={item.hint}
          >
            <span className="text-ink-600">{item.label}</span>
            <span className="font-mono tabular-nums text-ink-950">
              {formatRubFull(item.rub)}
            </span>
          </div>
        ),
      )}
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
