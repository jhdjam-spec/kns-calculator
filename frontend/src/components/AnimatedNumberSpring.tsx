"use client";

import { useEffect } from "react";
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  useReducedMotion,
} from "framer-motion";

interface Props {
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  locale?: string;
  className?: string;
  format?: "number" | "int" | "currency";
}

/**
 * Внутренний компонент с framer-motion useSpring. Грузится через dynamic
 * import только после first paint — чтобы не блокировать TBT.
 * Используется через обёртку components/AnimatedNumber.tsx.
 */
export function AnimatedNumberSpring({
  value,
  decimals = 0,
  prefix,
  suffix,
  locale = "ru-RU",
  className,
  format,
}: Props) {
  const reduceMotion = useReducedMotion();
  const mv = useMotionValue(value);
  const spring = useSpring(mv, {
    stiffness: 180,
    damping: 22,
    mass: 0.8,
    duration: reduceMotion ? 0 : undefined,
  });

  useEffect(() => {
    if (reduceMotion) {
      mv.jump(value);
    } else {
      mv.set(value);
    }
  }, [value, mv, reduceMotion]);

  const display = useTransform(spring, (n) => {
    if (!Number.isFinite(n)) return "—";
    if (format === "currency") {
      return `${Math.round(n).toLocaleString(locale)} ₽`;
    }
    if (format === "int" || decimals === 0) {
      return Math.round(n).toLocaleString(locale);
    }
    return n.toLocaleString(locale, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  });

  return (
    <span className={className}>
      {prefix}
      <motion.span>{display}</motion.span>
      {suffix}
    </span>
  );
}
