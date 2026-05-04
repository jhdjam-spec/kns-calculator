"use client";

import clsx from "clsx";
import type { PumpResult } from "@/schemas/result";
import { segmentLabels } from "@/schemas/result";

export interface PumpCardProps {
  segment: "budget" | "mid" | "premium";
  pump: PumpResult | null;
}

const SEGMENT_BORDERS = {
  budget: "border-budget",
  mid: "border-mid",
  premium: "border-premium",
} as const;

const SEGMENT_BG = {
  budget: "bg-budget/10",
  mid: "bg-mid/10",
  premium: "bg-premium/10",
} as const;

const AVAIL_BADGES: Record<string, { label: string; cls: string }> = {
  official: { label: "официально в РФ", cls: "bg-green-100 text-green-800" },
  parallel_import: { label: "параллельный импорт", cls: "bg-yellow-100 text-yellow-800" },
  stock_only: { label: "только со склада", cls: "bg-orange-100 text-orange-800" },
  discontinued: { label: "снят с производства", cls: "bg-red-100 text-red-800" },
};

const CONFIDENCE_LABELS: Record<"low" | "medium" | "high", { label: string; cls: string }> = {
  low: { label: "грубая оценка", cls: "bg-gray-100 text-gray-700" },
  medium: { label: "оценка по прайсу 2026", cls: "bg-blue-100 text-blue-800" },
  high: { label: "точная по БД", cls: "bg-green-100 text-green-800" },
};

function formatRub(rub: number): string {
  return new Intl.NumberFormat("ru-RU").format(rub);
}

export function PumpCard({ segment, pump }: PumpCardProps) {
  return (
    <article
      className={clsx(
        "rounded-lg border-2 p-5 flex flex-col gap-3",
        SEGMENT_BORDERS[segment],
        SEGMENT_BG[segment]
      )}
      data-testid={`segment-${segment}`}
    >
      <header className="flex items-baseline justify-between">
        <h3 className="text-lg font-bold capitalize">{segmentLabels[segment]}</h3>
        {pump && (
          <span className="text-sm text-gray-600">
            score: <strong>{pump.score.toFixed(2)}</strong>
          </span>
        )}
      </header>

      {pump ? (
        <>
          <div>
            <p className="text-xl font-semibold">{pump.brand}</p>
            <p className="text-base text-gray-700">{pump.model}</p>
          </div>

          <dl className="text-sm grid grid-cols-2 gap-x-4 gap-y-1">
            <dt className="text-gray-500">Мощность</dt>
            <dd>{pump.P_kW} кВт</dd>

            <dt className="text-gray-500">Тип</dt>
            <dd>{pump.type.replace(/_/g, " ")}</dd>

            <dt className="text-gray-500">Колесо</dt>
            <dd>{pump.impeller ?? "—"}</dd>

            <dt className="text-gray-500">Своб. проход</dt>
            <dd>{pump.free_passage_mm} мм</dd>

            {pump.discharge_DN_mm && (
              <>
                <dt className="text-gray-500">Напорный DN</dt>
                <dd>DN{pump.discharge_DN_mm}</dd>
              </>
            )}

            {pump.envelope.eta_BEP_pct !== null && pump.envelope.eta_BEP_pct !== undefined && (
              <>
                <dt className="text-gray-500">КПД (BEP)</dt>
                <dd>{pump.envelope.eta_BEP_pct}%</dd>
              </>
            )}
          </dl>

          {pump.price_estimate_rub > 0 && (
            <div className="mt-2 border-t border-gray-200 pt-2">
              <div className="flex items-baseline justify-between">
                <span className="text-xs text-gray-500">Ориентировочно комплект 1+1</span>
                <span
                  className={clsx(
                    "text-[10px] px-1.5 py-0.5 rounded-full font-medium",
                    CONFIDENCE_LABELS[pump.price_confidence].cls
                  )}
                  title="Уровень уверенности оценки: low — heuristic, medium — обвязка из АРКАДА КП 29.01.2026, high — все позиции из БД"
                >
                  {CONFIDENCE_LABELS[pump.price_confidence].label}
                </span>
              </div>
              <p className="text-2xl font-bold tabular-nums">
                {formatRub(pump.price_estimate_rub)} ₽
              </p>
              <details className="mt-1 text-xs text-gray-600">
                <summary className="cursor-pointer hover:text-gray-900 select-none">
                  разбивка по позициям
                </summary>
                <dl className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 pl-2 tabular-nums">
                  <dt>Насос (×2)</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.pump_rub)}</dd>
                  <dt>АТМ</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.atm_rub)}</dd>
                  <dt>Задвижка</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.valve_rub)}</dd>
                  <dt>Обр. клапан</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.check_valve_rub)}</dd>
                  <dt>Направляющие</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.rails_rub)}</dd>
                  <dt>Шкаф управления</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.cabinet_rub)}</dd>
                  <dt>Поплавки</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.floats_rub)}</dd>
                  <dt>Цепь</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.chain_rub)}</dd>
                  <dt>Корпус КНС</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.corpus_rub)}</dd>
                </dl>
              </details>
            </div>
          )}

          <footer className="flex flex-wrap gap-2 mt-auto pt-2">
            {AVAIL_BADGES[pump.available_ru_status] && (
              <span
                className={clsx(
                  "text-xs px-2 py-0.5 rounded-full font-medium",
                  AVAIL_BADGES[pump.available_ru_status].cls
                )}
              >
                {AVAIL_BADGES[pump.available_ru_status].label}
              </span>
            )}
            {pump.aor_zone && (
              <span
                className={clsx(
                  "text-xs px-2 py-0.5 rounded-full font-medium",
                  pump.aor_zone === "POR" && "bg-green-100 text-green-800",
                  pump.aor_zone === "AOR" && "bg-yellow-100 text-yellow-800",
                  pump.aor_zone === "outside" && "bg-red-100 text-red-800"
                )}
                title="Зона работы насоса (ANSI/HI 9.6.3): POR — preferred, AOR — allowable"
              >
                {pump.aor_zone}
              </span>
            )}
          </footer>
        </>
      ) : (
        <p className="text-sm text-gray-500 italic">
          Нет подходящих кандидатов в этом ценовом сегменте.
          <br />
          Расширьте параметры или передайте инженеру.
        </p>
      )}
    </article>
  );
}
