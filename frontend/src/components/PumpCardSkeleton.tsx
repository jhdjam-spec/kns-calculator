"use client";

import clsx from "clsx";

/**
 * Skeleton-loader для PumpCard. Использует `animate-shimmer` keyframes из
 * globals.css. Структура повторяет реальный PumpCard, чтобы layout shift
 * был минимальным при загрузке.
 */

const SEGMENT_BORDERS = {
  budget: "border-budget/40",
  mid: "border-mid/40",
  premium: "border-premium/40",
} as const;

interface Props {
  segment: "budget" | "mid" | "premium";
}

function Bar({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        "rounded bg-ink-200/60 dark:bg-white/[0.05] animate-shimmer",
        className,
      )}
    />
  );
}

export function PumpCardSkeleton({ segment }: Props) {
  return (
    <article
      className={clsx(
        "rounded-lg border-2 p-5 flex flex-col gap-3 bg-ink-50/30 dark:bg-white/[0.02]",
        SEGMENT_BORDERS[segment],
      )}
      aria-busy="true"
      aria-label="Загрузка результата подбора"
    >
      <header className="flex items-baseline justify-between">
        <Bar className="h-5 w-20" />
        <Bar className="h-3 w-10" />
      </header>

      <div className="space-y-2">
        <Bar className="h-6 w-32" />
        <Bar className="h-4 w-40" />
      </div>

      {/* Hero-strip Q/H/P/КПД */}
      <div className="grid grid-cols-4 gap-2 rounded-md bg-white/40 dark:bg-white/[0.03] px-3 py-2.5">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-1 text-center">
            <Bar className="h-5 w-10 mx-auto" />
            <Bar className="h-2 w-8 mx-auto" />
          </div>
        ))}
      </div>

      {/* Spec rows */}
      <div className="space-y-1.5">
        <Bar className="h-3 w-full" />
        <Bar className="h-3 w-5/6" />
        <Bar className="h-3 w-4/6" />
        <Bar className="h-3 w-3/5" />
      </div>

      {/* Price block */}
      <div className="mt-2 border-t border-ink-100 dark:border-white/[0.06] pt-3 space-y-2">
        <Bar className="h-3 w-1/2" />
        <Bar className="h-7 w-3/4" />
        <Bar className="h-2 w-2/3" />
      </div>

      <footer className="flex flex-wrap gap-2 mt-auto pt-2">
        <Bar className="h-5 w-24 rounded-full" />
        <Bar className="h-5 w-20 rounded-full" />
      </footer>
    </article>
  );
}
