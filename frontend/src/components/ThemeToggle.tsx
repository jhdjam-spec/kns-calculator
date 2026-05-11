// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { useEffect, useState } from "react";
import { Moon, Sun, Monitor } from "lucide-react";
import clsx from "clsx";

type ThemeMode = "light" | "dark" | "auto";

const STORAGE_KEY = "theme";

/**
 * Применяет тему к <html>:
 * - auto → удаляет .dark и .light, ставится prefers-color-scheme в CSS.
 * - light → ставит .light (отключает media-query dark fallback).
 * - dark  → ставит .dark.
 */
function applyTheme(mode: ThemeMode): void {
  const root = document.documentElement;
  root.classList.remove("dark", "light");
  if (mode === "dark") {
    root.classList.add("dark");
  } else if (mode === "light") {
    root.classList.add("light");
  }
}

function readStoredMode(): ThemeMode {
  if (typeof window === "undefined") return "auto";
  const v = window.localStorage.getItem(STORAGE_KEY);
  if (v === "light" || v === "dark" || v === "auto") return v;
  return "auto";
}

/**
 * Тогглер темы: auto → light → dark → auto (по кругу).
 * Состояние пишется в localStorage и применяется к <html class>.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const [mode, setMode] = useState<ThemeMode>("auto");

  useEffect(() => {
    const initial = readStoredMode();
    setMode(initial);
    applyTheme(initial);
  }, []);

  const cycle = () => {
    const next: ThemeMode = mode === "auto" ? "light" : mode === "light" ? "dark" : "auto";
    setMode(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, next);
    }
    applyTheme(next);
  };

  const label =
    mode === "auto" ? "Авто" : mode === "light" ? "Светлая" : "Тёмная";

  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={`Тема: ${label}. Нажмите чтобы переключить.`}
      title={`Тема: ${label}`}
      className={clsx(
        "inline-flex items-center justify-center h-11 w-11 md:h-9 md:w-9 rounded-md border border-white/10 text-ink-300 hover:text-accent-500 hover:border-accent-500/50 transition-colors duration-base",
        className,
      )}
    >
      {mode === "auto" && <Monitor size={16} strokeWidth={1.75} aria-hidden="true" />}
      {mode === "light" && <Sun size={16} strokeWidth={1.75} aria-hidden="true" />}
      {mode === "dark" && <Moon size={16} strokeWidth={1.75} aria-hidden="true" />}
    </button>
  );
}
