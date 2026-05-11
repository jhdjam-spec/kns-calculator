"use client";

/**
 * CostSankey — TCO-диаграмма для одного насоса (CAPEX + OPEX → TCO).
 *
 * Не использует d3-sankey: рисует простой 2-слойный flow-chart на нативном SVG
 * (Source-категории → CAPEX/OPEX → TCO). Хватает для bar-chart-стиля.
 *
 * Tabs: 1 год / 10 лет / тариф (slider). Backend: POST /tco/calculate.
 */
import { X } from "lucide-react";
import { useEffect, useId, useMemo, useState } from "react";
import { useMode } from "@/components/providers/ModeProvider";
import { tcoApi, type TCOResponse } from "@/lib/api-extended";
import type { PumpResult } from "@/schemas/result";

export interface CostSankeyProps {
  pump: PumpResult;
  segment: "budget" | "mid" | "premium";
  open: boolean;
  onClose: () => void;
  /** Если передан — позволяет повторно посчитать через selection_request. */
  selection?: unknown;
}

function formatRub(n: number): string {
  return new Intl.NumberFormat("ru-RU").format(Math.round(n));
}

function formatThousands(n: number): string {
  if (Math.abs(n) >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(2)} млн ₽`;
  }
  if (Math.abs(n) >= 1_000) {
    return `${(n / 1_000).toFixed(0)} тыс ₽`;
  }
  return `${formatRub(n)} ₽`;
}

export function CostSankey({ pump, segment, open, onClose, selection }: CostSankeyProps) {
  const { mode } = useMode();
  const titleId = useId();
  const [horizon, setHorizon] = useState<1 | 5 | 10>(10);
  const [tariff, setTariff] = useState<number>(7.5);
  const [data, setData] = useState<TCOResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    tcoApi
      .calculate({
        selection: selection ?? buildMinimalSelection(pump),
        segment,
        horizon_years: horizon,
        tariff_rub_per_kwh: tariff,
      })
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, pump, segment, horizon, tariff, selection]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const isEngineer = mode === "engineer";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      data-testid="cost-sankey"
      className="fixed inset-0 z-50 flex justify-end"
    >
      <button
        type="button"
        aria-label="Закрыть"
        onClick={onClose}
        className="absolute inset-0 bg-ink-950/60 backdrop-blur-sm"
      />
      <aside className="relative w-full max-w-2xl h-full bg-white shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-300">
        <header className="sticky top-0 bg-white border-b border-ink-200 px-6 py-4 flex items-center justify-between z-10">
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-ink-500">
              Стоимость владения (TCO)
            </div>
            <h3 id={titleId} className="font-display text-xl font-semibold text-ink-950">
              {pump.brand} {pump.model}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
            className="rounded-md p-2 hover:bg-ink-100 transition-colors"
          >
            <X size={20} strokeWidth={1.75} />
          </button>
        </header>

        <div className="px-6 py-5 space-y-5">
          {/* Tabs горизонта */}
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Горизонт TCO">
            {[1, 5, 10].map((y) => (
              <button
                key={y}
                role="tab"
                aria-selected={horizon === y}
                data-testid={`horizon-${y}`}
                onClick={() => setHorizon(y as 1 | 5 | 10)}
                className={
                  horizon === y
                    ? "px-4 py-1.5 text-sm font-medium rounded-md bg-brand-700 text-white"
                    : "px-4 py-1.5 text-sm font-medium rounded-md bg-ink-100 text-ink-700 hover:bg-ink-200"
                }
                type="button"
              >
                {y} {y === 1 ? "год" : y < 5 ? "года" : "лет"}
              </button>
            ))}
          </div>

          {/* Slider тарифа */}
          <div>
            <label htmlFor="tariff-input" className="block text-xs font-mono uppercase tracking-wider text-ink-500 mb-1.5">
              Тариф электроэнергии: {tariff.toFixed(2)} ₽/кВт·ч
            </label>
            <input
              id="tariff-input"
              type="range"
              min={3}
              max={15}
              step={0.5}
              value={tariff}
              onChange={(e) => setTariff(Number(e.target.value))}
              className="w-full accent-accent-500"
              aria-label="Тариф электроэнергии"
            />
            <div className="flex justify-between text-xs text-ink-500 mt-0.5">
              <span>3 ₽</span>
              <span>15 ₽</span>
            </div>
          </div>

          {loading && (
            <div className="text-sm text-ink-500 py-4">Расчёт TCO…</div>
          )}
          {error && (
            <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700">
              Ошибка TCO: {error}
            </div>
          )}

          {data && !loading && <SankeyView data={data} isEngineer={isEngineer} />}

          <div className="text-xs text-ink-500 italic pt-2 border-t border-ink-200">
            ⚠️ Оценка ±30% — реальные затраты могут отличаться в зависимости от
            местного тарифа, графика работы и условий эксплуатации.
            Точный TCO считает инженер по ISO 15686.
          </div>
        </div>
      </aside>
    </div>
  );
}

function buildMinimalSelection(pump: PumpResult): unknown {
  // Минимальная заглушка SelectionResult — backend возьмёт указанный сегмент.
  // Реальный SelectionResult приходит из useSelection / результата подбора,
  // но прямой клик «Стоимость на 10 лет» из карточки даёт минимум.
  const empty: PumpResult | null = null;
  return {
    schema_version: "1.2",
    input: {},
    computed: {
      D_mm: 0, v_ms: 0, Re: 0, friction_factor: 0,
      H_tr_m: 0, sum_zeta: 0, H_m_m: 0, H_full_m: 0, safety_factor: 1.0,
    },
    results: {
      budget: pump.price_segment === "budget" ? pump : empty,
      mid: pump.price_segment === "mid" ? pump : empty,
      premium: pump.price_segment === "premium" ? pump : empty,
    },
    candidates_total: 1,
    warnings: [],
    engineer_handoff_required: false,
    trigger_reasons: [],
    assumptions: [],
    completeness_pct: 50,
    summary_text: "",
    alternatives: [],
    suggestions: [],
  };
}

function SankeyView({ data, isEngineer }: { data: TCOResponse; isEngineer: boolean }) {
  // Источники CAPEX и OPEX
  const capexItems = useMemo(
    () =>
      [
        { id: "pump", name: "Насосы", value: data.capex.pump_rub || 0 },
        { id: "corpus", name: "Корпус КНС", value: data.capex.corpus_rub || 0 },
        { id: "cabinet", name: "Шкаф", value: data.capex.cabinet_rub || 0 },
        { id: "fittings", name: "Обвязка", value: data.capex.fittings_rub || 0 },
        { id: "install", name: "Монтаж + ПНР", value: data.capex.install_rub || 0 },
        { id: "transport", name: "Доставка", value: data.capex.transport_rub || 0 },
      ].filter((x) => x.value > 0),
    [data.capex],
  );

  // OPEX за горизонт = annual × years
  const horizon = data.horizon_years;
  const opexItems = useMemo(
    () =>
      [
        { id: "electricity", name: "Электричество", value: (data.opex_annual.electricity_rub || 0) * horizon },
        { id: "maintenance", name: "ТО", value: (data.opex_annual.maintenance_rub || 0) * horizon },
        { id: "depreciation", name: "Замена насоса", value: (data.opex_annual.depreciation_rub || 0) * horizon },
        { id: "cleaning", name: "Промывка корпуса", value: (data.opex_annual.cleaning_rub || 0) * horizon },
        { id: "electronics", name: "Износ электроники", value: (data.opex_annual.electronics_rub || 0) * horizon },
      ].filter((x) => x.value > 0),
    [data.opex_annual, horizon],
  );

  const capexTotal = data.capex.total_rub || capexItems.reduce((s, x) => s + x.value, 0);
  const opexTotal = data.opex_horizon_rub || opexItems.reduce((s, x) => s + x.value, 0);
  const tcoTotal = data.tco_horizon_rub || capexTotal + opexTotal;

  const maxVal = Math.max(capexTotal, opexTotal, 0.0001);

  return (
    <section data-testid="sankey-view">
      {/* Главный KPI: cost_per_m³ */}
      <div className="rounded-card bg-accent-500/5 border border-accent-500/30 p-4 mb-5">
        <div className="text-xs font-mono uppercase tracking-wider text-ink-500 mb-1">
          Стоимость 1 м³ стоков
        </div>
        <div className="font-display text-3xl font-semibold text-ink-950 tabular-nums">
          {data.cost_per_m3_rub.toFixed(2)} ₽
        </div>
        <div className="text-sm text-ink-600 mt-1">
          За {horizon} {horizon === 1 ? "год" : "лет"}: TCO = {formatThousands(tcoTotal)}
          {" · "}через КНС: {formatThousands(data.flow_horizon_m3)} м³
        </div>
      </div>

      {/* CAPEX → разбивка */}
      <FlowBlock
        title={`CAPEX → ${formatThousands(capexTotal)}`}
        items={capexItems}
        total={capexTotal}
        maxVal={maxVal}
        accent="brand"
      />

      {/* OPEX → разбивка за горизонт */}
      <FlowBlock
        title={`OPEX за ${horizon} лет → ${formatThousands(opexTotal)}`}
        items={opexItems}
        total={opexTotal}
        maxVal={maxVal}
        accent="accent"
      />

      {/* Итог */}
      <div className="mt-5 p-4 rounded-card border-2 border-ink-950 bg-ink-950 text-ink-50">
        <div className="text-xs font-mono uppercase tracking-wider text-ink-300 mb-1">
          TCO за {horizon} лет
        </div>
        <div className="font-display text-3xl font-semibold tabular-nums">
          {formatThousands(tcoTotal)}
        </div>
        <div className="text-sm text-ink-300 mt-1">
          CAPEX {((capexTotal / tcoTotal) * 100).toFixed(0)}%
          {" · "}
          OPEX {((opexTotal / tcoTotal) * 100).toFixed(0)}%
        </div>
      </div>

      {isEngineer && (
        <div className="mt-4 text-xs text-ink-500 space-y-0.5">
          <div>· Тариф: {data.tariff_rub_per_kwh.toFixed(2)} ₽/кВт·ч</div>
          <div>· Часов работы в год: {data.hours_per_year.toFixed(0)} ({data.operating_mode})</div>
          <div>· Расход за горизонт: {formatRub(data.flow_horizon_m3)} м³</div>
        </div>
      )}
    </section>
  );
}

function FlowBlock({
  title,
  items,
  total,
  maxVal,
  accent,
}: {
  title: string;
  items: { id: string; name: string; value: number }[];
  total: number;
  maxVal: number;
  accent: "brand" | "accent";
}) {
  const barClass = accent === "accent" ? "bg-accent-500" : "bg-brand-700";
  const widthOuter = (total / maxVal) * 100;
  return (
    <div className="mb-5">
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-sm font-medium text-ink-950">{title}</span>
      </div>
      <div className="h-1.5 rounded-full bg-ink-100 mb-3 overflow-hidden">
        <div
          className={`${barClass} h-full`}
          // eslint-disable-next-line react/forbid-dom-props
          style={{ width: `${widthOuter}%` }}
        />
      </div>
      <ul className="space-y-1.5 pl-3 border-l-2 border-ink-200">
        {items.map((it) => {
          const pct = total > 0 ? (it.value / total) * 100 : 0;
          return (
            <li
              key={it.id}
              data-flow-item={it.id}
              className="flex items-baseline justify-between gap-3 group"
              title={`${it.name}: ${formatThousands(it.value)} (${pct.toFixed(1)}%)`}
            >
              <span className="text-sm text-ink-700 flex-1 truncate">{it.name}</span>
              <div className="flex items-baseline gap-2 tabular-nums">
                <span className="text-xs text-ink-500">{pct.toFixed(0)}%</span>
                <span className="text-sm font-mono text-ink-950">
                  {formatThousands(it.value)}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
