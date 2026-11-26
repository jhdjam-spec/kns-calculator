"use client";

import { useEffect, useState } from "react";

interface Props {
  /** Целевое значение */
  value: number;
  /** Кол-во знаков после запятой */
  decimals?: number;
  /** Префикс (опц.) — например «Q=» */
  prefix?: string;
  /** Суффикс (опц.) — например « м³/ч» */
  suffix?: string;
  /** Локаль для группировки разрядов (по умолчанию ru-RU) */
  locale?: string;
  /** className для оборачивающего span */
  className?: string;
  /** Тип форматирования: number / int / currency */
  format?: "number" | "int" | "currency";
}

function formatValue(n: number, format: Props["format"], decimals: number, locale: string): string {
  if (!Number.isFinite(n)) return "—";
  if (format === "currency") return `${Math.round(n).toLocaleString(locale)} ₽`;
  if (format === "int" || decimals === 0) return Math.round(n).toLocaleString(locale);
  return n.toLocaleString(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Плавная тик-анимация числа (Stripe pricing-style).
 *
 * Производительность: framer-motion (~50 KB) грузится lazy после первого
 * рендера. До этого момента показывается финальное число обычным текстом.
 * Это снимает TBT критпуть Hero (~1.6с → ~0.4с на 4G mobile).
 *
 * Уважает prefers-reduced-motion: при reduce-motion вообще не грузим framer.
 */
export function AnimatedNumber({
  value,
  decimals = 0,
  prefix,
  suffix,
  locale = "ru-RU",
  className,
  format,
}: Props) {
  const [Animated, setAnimated] = useState<React.ComponentType<Props> | null>(null);

  useEffect(() => {
    // prefers-reduced-motion → не подключаем framer-motion вообще
    if (typeof window !== "undefined" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }
    // Идле-загрузка после hydration — снимаем TBT с критпути
    const schedule = (cb: () => void) =>
      "requestIdleCallback" in window
        ? (window as Window & { requestIdleCallback: (cb: () => void) => void }).requestIdleCallback(cb)
        : setTimeout(cb, 200);

    schedule(() => {
      import("./AnimatedNumberSpring").then((m) => setAnimated(() => m.AnimatedNumberSpring));
    });
  }, []);

  if (Animated) {
    return <Animated value={value} decimals={decimals} prefix={prefix} suffix={suffix} locale={locale} className={className} format={format} />;
  }

  return (
    <span className={className}>
      {prefix}
      {formatValue(value, format, decimals, locale)}
      {suffix}
    </span>
  );
}
