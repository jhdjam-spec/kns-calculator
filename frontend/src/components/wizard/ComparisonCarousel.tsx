"use client";

/**
 * ComparisonCarousel — сравнение 3+ насосов рядом с мини-radar-диаграммой
 * по 6 осям (BEP, η, H margin, availability, warranty, price-fit).
 *
 * Desktop (≥768px): 3 колонки side-by-side.
 * Mobile (<768px): swipeable carousel, 1 карточка на view, dots indicator.
 *
 * Используется нативный SVG для radar chart — экономит ~80 KB bundle
 * (vs. recharts) и даёт полный контроль над стилем. 6 осей, все
 * нормализованы 0–100.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import type { PumpResult } from "@/schemas/result";
import { segmentLabels } from "@/schemas/result";

// ─── Radar metrics ──────────────────────────────────────────────────────

export interface RadarMetrics {
  /** Близость к точке наилучшего КПД (BEP): чем ближе Q к Q_BEP, тем выше. */
  bep: number;
  /** КПД в BEP, % → масштаб 0–100. */
  eta: number;
  /** Запас по напору (H_max / H_full ≈ 1.10 идеал). */
  h_margin: number;
  /** Доступность в РФ. */
  availability: number;
  /** Гарантия (мес / 24 × 100). */
  warranty: number;
  /** Соответствие сегмента цене. */
  price_fit: number;
}

const AVAILABILITY_SCORE: Record<string, number> = {
  official: 100,
  parallel_import: 60,
  stock_only: 40,
  discontinued: 0,
};

const SEGMENT_PRICE_FIT: Record<"budget" | "mid" | "premium", number> = {
  budget: 90,
  mid: 80,
  premium: 70,
};

/**
 * Гарантия по умолчанию — если в schema нет warranty_months, оценочно
 * по сегменту: budget=12, mid=18, premium=24.
 */
function inferWarrantyMonths(pump: PumpResult): number {
  // Schema не содержит warranty_months явно; используем эвристику по сегменту
  switch (pump.price_segment) {
    case "premium":
      return 24;
    case "mid":
      return 18;
    case "budget":
    default:
      return 12;
  }
}

export function computeRadarMetrics(pump: PumpResult): RadarMetrics {
  const env = pump.envelope;
  const dp = pump.duty_point ?? {};
  const Q = Number(dp.Q_m3h ?? 0);
  const H = Number(dp.H_m ?? 0);

  // BEP proximity: 1 - |Q - Q_BEP| / Q_BEP, capped 0..1
  let bep = 0;
  if (env.Q_BEP_m3h && env.Q_BEP_m3h > 0 && Q > 0) {
    const delta = Math.abs(Q - env.Q_BEP_m3h) / env.Q_BEP_m3h;
    bep = Math.max(0, 1 - delta) * 100;
  } else if (pump.aor_zone === "POR") {
    bep = 90;
  } else if (pump.aor_zone === "AOR") {
    bep = 65;
  } else {
    bep = 40;
  }

  // η_BEP
  const eta = env.eta_BEP_pct ? Math.min(100, env.eta_BEP_pct) : 50;

  // H margin: идеал = H_max / H ≈ 1.10. score = 1 - |ratio - 1.10|, capped.
  let h_margin = 50;
  if (env.H_max_m && H > 0) {
    const ratio = env.H_max_m / H;
    h_margin = Math.max(0, 1 - Math.abs(ratio - 1.1)) * 100;
  }

  // Availability
  const availability = AVAILABILITY_SCORE[pump.available_ru_status] ?? 50;

  // Warranty
  const months = inferWarrantyMonths(pump);
  const warranty = Math.min(100, (months / 24) * 100);

  // Price-fit по сегменту
  const price_fit = SEGMENT_PRICE_FIT[pump.price_segment] ?? 50;

  return {
    bep: Math.round(bep),
    eta: Math.round(eta),
    h_margin: Math.round(h_margin),
    availability: Math.round(availability),
    warranty: Math.round(warranty),
    price_fit: Math.round(price_fit),
  };
}

/** Composite score 0..100 — простой mean 6 осей. */
export function computeCompositeScore(metrics: RadarMetrics): number {
  const sum =
    metrics.bep +
    metrics.eta +
    metrics.h_margin +
    metrics.availability +
    metrics.warranty +
    metrics.price_fit;
  return Math.round(sum / 6);
}

// ─── Mini radar chart (нативный SVG) ─────────────────────────────────────

const AXES: Array<{ key: keyof RadarMetrics; label: string; hint: string }> = [
  { key: "bep", label: "BEP", hint: "Близость к точке наилучшего КПД" },
  { key: "eta", label: "η", hint: "КПД в BEP" },
  { key: "h_margin", label: "H", hint: "Запас по напору" },
  { key: "availability", label: "Дост.", hint: "Доступность в РФ" },
  { key: "warranty", label: "Гар.", hint: "Гарантия" },
  { key: "price_fit", label: "Цена", hint: "Соответствие сегменту" },
];

interface MiniRadarProps {
  metrics: RadarMetrics;
  size?: number;
  /** Подсветка (mid сегмент). */
  highlight?: boolean;
}

export function MiniRadar({ metrics, size = 160, highlight = false }: MiniRadarProps) {
  const cx = size / 2;
  const cy = size / 2;
  // Оставляем поле под подписи осей
  const r = size / 2 - 22;
  const n = AXES.length;

  // Координаты вершин по 6 осям. Угол: 0 = вверх, далее по часовой.
  const angle = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / n;

  // Точки многоугольника значений
  const points = AXES.map((axis, i) => {
    const v = metrics[axis.key] / 100;
    const rr = r * Math.max(0, Math.min(1, v));
    const a = angle(i);
    return [cx + rr * Math.cos(a), cy + rr * Math.sin(a)];
  });

  // Концентрические сетки (25/50/75/100%)
  const gridLevels = [0.25, 0.5, 0.75, 1.0];

  const fillColor = highlight ? "rgb(201 162 74 / 0.25)" : "rgb(24 69 85 / 0.20)";
  const strokeColor = highlight ? "rgb(201 162 74)" : "rgb(24 69 85)";

  const polyPoints = points.map((p) => p.join(",")).join(" ");

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label="Радар-диаграмма по 6 осям"
      data-testid="mini-radar"
    >
      {/* Концентрические сетки */}
      {gridLevels.map((level) => {
        const grid = AXES.map((_, i) => {
          const a = angle(i);
          return [cx + r * level * Math.cos(a), cy + r * level * Math.sin(a)];
        });
        return (
          <polygon
            key={level}
            points={grid.map((p) => p.join(",")).join(" ")}
            fill="none"
            stroke="rgb(232 232 229)"
            strokeWidth="1"
            opacity={level === 1 ? 0.8 : 0.4}
          />
        );
      })}

      {/* Лучи (от центра к вершинам) */}
      {AXES.map((_, i) => {
        const a = angle(i);
        return (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={cx + r * Math.cos(a)}
            y2={cy + r * Math.sin(a)}
            stroke="rgb(232 232 229)"
            strokeWidth="1"
            opacity={0.5}
          />
        );
      })}

      {/* Многоугольник значений */}
      <polygon
        points={polyPoints}
        fill={fillColor}
        stroke={strokeColor}
        strokeWidth="2"
        strokeLinejoin="round"
      />

      {/* Точки на вершинах */}
      {points.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="3" fill={strokeColor} />
      ))}

      {/* Подписи осей */}
      {AXES.map((axis, i) => {
        const a = angle(i);
        const labelR = r + 12;
        const x = cx + labelR * Math.cos(a);
        const y = cy + labelR * Math.sin(a);
        return (
          <text
            key={axis.key}
            x={x}
            y={y}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="10"
            fontFamily="ui-monospace, monospace"
            fill="rgb(117 117 113)"
            data-testid={`radar-axis-${axis.key}`}
          >
            <title>{axis.hint}</title>
            {axis.label}
          </text>
        );
      })}
    </svg>
  );
}

// ─── Comparison card ─────────────────────────────────────────────────────

interface ComparisonCardProps {
  pump: PumpResult;
  metrics: RadarMetrics;
  composite: number;
  active?: boolean;
  onSelect: (pump: PumpResult) => void;
}

function ComparisonCard({
  pump,
  metrics,
  composite,
  active = false,
  onSelect,
}: ComparisonCardProps) {
  const segmentLabel = segmentLabels[pump.price_segment];
  const isMid = pump.price_segment === "mid";

  return (
    <article
      data-testid={`compare-card-${pump.id}`}
      className={clsx(
        "rounded-card bg-white border p-5 md:p-6 flex flex-col gap-3 h-full transition-shadow duration-base",
        active
          ? "border-accent-500 shadow-premium-md ring-1 ring-accent-500/30"
          : "border-ink-200 hover:shadow-premium-sm",
      )}
    >
      <header className="flex items-baseline justify-between gap-2">
        <span
          className={clsx(
            "text-[10px] font-mono uppercase tracking-widest font-medium",
            isMid ? "text-accent-600" : "text-ink-500",
          )}
        >
          {segmentLabel}
        </span>
        <span
          className={clsx(
            "text-xs px-2 py-0.5 rounded-full font-mono tabular-nums",
            composite >= 75
              ? "bg-green-100 text-green-800"
              : composite >= 50
              ? "bg-yellow-100 text-yellow-800"
              : "bg-red-100 text-red-800",
          )}
          title="Composite score — среднее по 6 осям radar"
          data-testid={`composite-${pump.id}`}
        >
          {composite}%
        </span>
      </header>

      <div>
        <div className="font-display text-lg font-semibold text-ink-950 leading-tight">
          {pump.brand}
        </div>
        <div className="text-sm text-ink-700 mt-0.5">{pump.model}</div>
      </div>

      <div className="flex justify-center py-2">
        <MiniRadar metrics={metrics} size={160} highlight={isMid} />
      </div>

      {pump.price_estimate_rub > 0 && (
        <div className="border-t border-ink-200 pt-3">
          <div className="text-[10px] font-mono uppercase tracking-wider text-ink-500">
            Комплект, ориентир
          </div>
          <div className="font-display text-xl font-semibold text-ink-950 tabular-nums">
            {new Intl.NumberFormat("ru-RU").format(pump.price_estimate_rub)} ₽
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => onSelect(pump)}
        className={clsx(
          "mt-auto w-full px-4 py-2 rounded-md text-sm font-medium transition-colors",
          active
            ? "bg-accent-500 text-ink-950 hover:bg-accent-400"
            : "bg-ink-100 text-ink-950 hover:bg-ink-200 border border-ink-300",
        )}
        data-testid={`select-${pump.id}`}
      >
        {active ? "✓ Выбран" : "Выбрать"}
      </button>
    </article>
  );
}

// ─── Mobile swipe carousel ────────────────────────────────────────────────

interface MobileCarouselProps {
  cards: Array<{
    pump: PumpResult;
    metrics: RadarMetrics;
    composite: number;
  }>;
  activeId?: string;
  onSelect: (pump: PumpResult) => void;
}

function MobileCarousel({ cards, activeId, onSelect }: MobileCarouselProps) {
  const [index, setIndex] = useState(0);
  const trackRef = useRef<HTMLDivElement | null>(null);
  const startX = useRef<number | null>(null);

  const goTo = useCallback(
    (i: number) => {
      const clamped = Math.max(0, Math.min(cards.length - 1, i));
      setIndex(clamped);
    },
    [cards.length],
  );

  const onTouchStart = (e: React.TouchEvent) => {
    startX.current = e.touches[0].clientX;
  };
  const onTouchEnd = (e: React.TouchEvent) => {
    if (startX.current === null) return;
    const dx = e.changedTouches[0].clientX - startX.current;
    const threshold = 40;
    if (dx > threshold) goTo(index - 1);
    else if (dx < -threshold) goTo(index + 1);
    startX.current = null;
  };

  return (
    <div className="md:hidden">
      <div
        ref={trackRef}
        className="overflow-hidden"
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        data-testid="mobile-carousel-track"
      >
        <div
          className="flex transition-transform duration-base ease-out"
          // eslint-disable-next-line react/forbid-dom-props
          style={{ transform: `translateX(-${index * 100}%)` }}
        >
          {cards.map(({ pump, metrics, composite }) => (
            <div key={pump.id} className="w-full flex-shrink-0 px-1">
              <ComparisonCard
                pump={pump}
                metrics={metrics}
                composite={composite}
                active={activeId === pump.id}
                onSelect={onSelect}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Dots indicator */}
      <div
        className="flex justify-center gap-2 mt-4"
        role="tablist"
        aria-label="Навигация по карточкам сравнения"
      >
        {cards.map((c, i) => (
          <button
            key={c.pump.id}
            type="button"
            role="tab"
            aria-selected={i === index}
            aria-label={`Карточка ${i + 1}: ${c.pump.brand} ${c.pump.model}`}
            onClick={() => goTo(i)}
            data-testid={`carousel-dot-${i}`}
            className={clsx(
              "h-2 rounded-full transition-all duration-base",
              i === index ? "bg-accent-500 w-6" : "bg-ink-300 w-2",
            )}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Public component ────────────────────────────────────────────────────

export interface ComparisonCarouselProps {
  pumps: PumpResult[];
  /** id насоса, выбранного в данный момент (визуально активная карточка). */
  activePumpId?: string;
  /** Колбэк нажатия на «Выбрать». Если не передан — кнопка остаётся, но без эффекта. */
  onSelect?: (pump: PumpResult) => void;
  className?: string;
}

export function ComparisonCarousel({
  pumps,
  activePumpId,
  onSelect,
  className,
}: ComparisonCarouselProps) {
  const cards = useMemo(
    () =>
      pumps.map((pump) => {
        const metrics = computeRadarMetrics(pump);
        const composite = computeCompositeScore(metrics);
        return { pump, metrics, composite };
      }),
    [pumps],
  );

  const handleSelect = useCallback(
    (pump: PumpResult) => {
      if (onSelect) onSelect(pump);
    },
    [onSelect],
  );

  // localStorage-кэш выбора для мини-state-persistence (не критично)
  const [internalActive, setInternalActive] = useState<string | undefined>(activePumpId);
  useEffect(() => {
    setInternalActive(activePumpId);
  }, [activePumpId]);

  const onCardSelect = (pump: PumpResult) => {
    setInternalActive(pump.id);
    handleSelect(pump);
  };

  if (cards.length === 0) {
    return (
      <div className="text-ink-500 text-sm italic p-6 text-center">
        Нет насосов для сравнения.
      </div>
    );
  }

  return (
    <section
      className={clsx("w-full", className)}
      aria-label="Сравнение насосов"
      data-testid="comparison-carousel"
    >
      {/* Desktop: grid 3 cols */}
      <div className="hidden md:grid md:grid-cols-3 gap-4 md:gap-6">
        {cards.map(({ pump, metrics, composite }) => (
          <ComparisonCard
            key={pump.id}
            pump={pump}
            metrics={metrics}
            composite={composite}
            active={internalActive === pump.id}
            onSelect={onCardSelect}
          />
        ))}
      </div>

      {/* Mobile: swipeable carousel */}
      <MobileCarousel
        cards={cards}
        activeId={internalActive}
        onSelect={onCardSelect}
      />

      {/* Легенда */}
      <details className="mt-6 text-xs text-ink-500">
        <summary className="cursor-pointer hover:text-ink-700 select-none">
          Как читать radar-диаграмму →
        </summary>
        <dl className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 pl-3">
          {AXES.map((a) => (
            <div key={a.key} className="flex gap-2">
              <dt className="font-mono text-ink-700 shrink-0 w-12">{a.label}</dt>
              <dd className="text-ink-600">{a.hint}</dd>
            </div>
          ))}
        </dl>
      </details>
    </section>
  );
}
