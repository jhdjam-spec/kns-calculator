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

const AVAIL_BADGES: Record<string, { label: string; cls: string; hint: string }> = {
  official: {
    label: "Официальная поставка",
    cls: "bg-green-100 text-green-800",
    hint: "В наличии у российского дилера. Срок поставки обычно 2–6 недель.",
  },
  parallel_import: {
    label: "Параллельный импорт",
    cls: "bg-yellow-100 text-yellow-800",
    hint: "Через параллельный импорт. Срок поставки 8–14 недель, цена выше каталожной.",
  },
  stock_only: {
    label: "Только со склада",
    cls: "bg-orange-100 text-orange-800",
    hint: "Только остатки на складе дилера. Уточняйте наличие — количество ограничено.",
  },
  discontinued: {
    label: "Снят с производства",
    cls: "bg-red-100 text-red-800",
    hint: "Производитель снял модель. Запросите у инженера актуальный аналог.",
  },
};

const CONFIDENCE_LABELS: Record<"low" | "medium" | "high", { label: string; cls: string; hint: string }> = {
  low: {
    label: "ориентировочно",
    cls: "bg-gray-100 text-gray-700",
    hint: "Грубая оценка — точные цены уточнит инженер при подготовке КП.",
  },
  medium: {
    label: "по прайсу 2026",
    cls: "bg-blue-100 text-blue-800",
    hint: "Цены обвязки взяты из коммерческого прайса 2026. Цена насоса — оценочная.",
  },
  high: {
    label: "проверено по КП",
    cls: "bg-green-100 text-green-800",
    hint: "И насос, и обвязка — точные цены из реальных КП поставщиков 2026.",
  },
};

const ZONE_LABELS: Record<"POR" | "AOR" | "outside", { label: string; cls: string; hint: string }> = {
  POR: {
    label: "Оптимально",
    cls: "bg-green-100 text-green-800",
    hint: "Насос работает в точке наилучшего КПД — максимальная эффективность и срок службы.",
  },
  AOR: {
    label: "Допустимо",
    cls: "bg-yellow-100 text-yellow-800",
    hint: "Насос работает в допустимом режиме, но КПД на 5–10% ниже оптимума.",
  },
  outside: {
    label: "Не рекомендуем",
    cls: "bg-red-100 text-red-800",
    hint: "Точка работы за пределами рекомендуемого режима — повышенный износ.",
  },
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
          <span
            className="text-xs text-gray-500"
            title={`Совпадение с запросом: ${(pump.score * 100).toFixed(0)}%. Учитывает близость к точке наилучшего КПД, доступность в РФ, гарантию.`}
          >
            ★ {(pump.score * 100).toFixed(0)}%
          </span>
        )}
      </header>

      {pump ? (
        <>
          <div>
            <p className="text-xl font-semibold">{pump.brand}</p>
            <p className="text-base text-gray-700">{pump.model}</p>
          </div>

          <dl className="text-sm grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
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
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-xs text-gray-600">
                  Цена комплекта (рабочий + резервный насос)
                </span>
                <span
                  className={clsx(
                    "text-[10px] px-1.5 py-0.5 rounded-full font-medium whitespace-nowrap",
                    CONFIDENCE_LABELS[pump.price_confidence].cls
                  )}
                  title={CONFIDENCE_LABELS[pump.price_confidence].hint}
                >
                  {CONFIDENCE_LABELS[pump.price_confidence].label}
                </span>
              </div>
              {/* Phase 9: показываем диапазон цены если spread > 5%, иначе точную */}
              {(() => {
                const low = pump.price_breakdown.total_low_rub;
                const high = pump.price_breakdown.total_high_rub;
                const total = pump.price_estimate_rub;
                const showRange = high - low > total * 0.05 && low > 0 && high > 0;
                if (showRange) {
                  return (
                    <>
                      <p className="text-xl md:text-2xl font-bold tabular-nums leading-tight">
                        {formatRub(low)} – {formatRub(high)} ₽
                      </p>
                      <p className="text-xs text-gray-500 tabular-nums">
                        ориентир ≈ {formatRub(total)} ₽
                      </p>
                    </>
                  );
                }
                return (
                  <p className="text-2xl font-bold tabular-nums">
                    {formatRub(total)} ₽
                  </p>
                );
              })()}
              <p className="text-[10px] text-gray-500 mt-0.5">
                Без монтажа, доставки и пуско-наладки. Точную цену согласует инженер.
              </p>
              <details className="mt-1 text-xs text-gray-600">
                <summary className="cursor-pointer hover:text-gray-900 select-none">
                  Из чего состоит комплект →
                </summary>
                <dl className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 pl-2 tabular-nums">
                  <dt>2 насоса (рабочий + резервный)</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.pump_rub)}</dd>
                  <dt>Трубные муфты</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.atm_rub)}</dd>
                  <dt>Задвижки</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.valve_rub)}</dd>
                  <dt>Обратные клапаны</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.check_valve_rub)}</dd>
                  {pump.price_breakdown.rails_rub > 0 && (
                    <>
                      <dt>Направляющие</dt>
                      <dd className="text-right">{formatRub(pump.price_breakdown.rails_rub)}</dd>
                    </>
                  )}
                  <dt>Шкаф управления</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.cabinet_rub)}</dd>
                  <dt>Поплавки уровня</dt>
                  <dd className="text-right">{formatRub(pump.price_breakdown.floats_rub)}</dd>
                  {pump.price_breakdown.chain_rub > 0 && (
                    <>
                      <dt>Цепь</dt>
                      <dd className="text-right">{formatRub(pump.price_breakdown.chain_rub)}</dd>
                    </>
                  )}
                  {pump.price_breakdown.corpus_rub > 0 && (
                    <>
                      <dt>Корпус КНС</dt>
                      <dd className="text-right">{formatRub(pump.price_breakdown.corpus_rub)}</dd>
                    </>
                  )}
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
                title={AVAIL_BADGES[pump.available_ru_status].hint}
              >
                {AVAIL_BADGES[pump.available_ru_status].label}
              </span>
            )}
            {pump.aor_zone && ZONE_LABELS[pump.aor_zone] && (
              <span
                className={clsx(
                  "text-xs px-2 py-0.5 rounded-full font-medium",
                  ZONE_LABELS[pump.aor_zone].cls
                )}
                title={ZONE_LABELS[pump.aor_zone].hint}
              >
                {ZONE_LABELS[pump.aor_zone].label}
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
