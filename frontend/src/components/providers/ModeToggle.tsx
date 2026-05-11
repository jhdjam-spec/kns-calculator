"use client";

/**
 * ModeToggle — iOS-like switch для глобального переключения аудитории.
 *
 * Менеджер ↔ Инженер. Использует `useMode()` из ModeProvider.
 * Touch target ≥44px на mobile, ≥36px на desktop. aria-pressed для
 * screen readers (это бинарный toggle, не tablist).
 *
 * Дизайн:
 *  - Pill с двумя зонами «Менеджер | Инженер».
 *  - Активная зона — bg-ink-50 на тёмном/bg-ink-950 на светлом.
 *  - Используется в SiteNav рядом с ThemeToggle.
 */

import clsx from "clsx";
import { useMode, type AppMode } from "./ModeProvider";

export interface ModeToggleProps {
  className?: string;
  /** Скрыть подписи на узких экранах, показать только короткие «М / И». */
  compact?: boolean;
}

export function ModeToggle({ className, compact = false }: ModeToggleProps) {
  const { mode, setMode } = useMode();

  return (
    <div
      role="radiogroup"
      aria-label="Режим интерфейса: Менеджер или Инженер"
      data-testid="mode-toggle"
      className={clsx(
        "inline-flex items-center bg-white/5 border border-white/10 rounded-md p-0.5 h-11 md:h-9",
        className,
      )}
    >
      <ToggleOption
        active={mode === "manager"}
        onClick={() => setMode("manager")}
        label="Менеджер"
        short="М"
        compact={compact}
      />
      <ToggleOption
        active={mode === "engineer"}
        onClick={() => setMode("engineer")}
        label="Инженер"
        short="И"
        compact={compact}
      />
    </div>
  );
}

interface ToggleOptionProps {
  active: boolean;
  onClick: () => void;
  label: string;
  short: string;
  compact: boolean;
}

function ToggleOption({ active, onClick, label, short, compact }: ToggleOptionProps) {
  const isManager = label === "Менеджер";
  const value: AppMode = isManager ? "manager" : "engineer";
  return (
    <button
      type="button"
      role="radio"
      aria-checked={active ? "true" : "false"}
      aria-label={`Переключиться в режим ${label}`}
      data-mode={value}
      data-active={active}
      onClick={onClick}
      className={clsx(
        "inline-flex items-center justify-center h-10 md:h-8 px-2.5 md:px-3 rounded text-xs font-medium tracking-wide transition-colors min-w-[44px] md:min-w-[60px]",
        active
          ? "bg-ink-50 text-ink-950 shadow-sm"
          : "text-ink-300 hover:text-ink-50",
      )}
    >
      {compact ? (
        <>
          <span className="sm:hidden">{short}</span>
          <span className="hidden sm:inline">{label}</span>
        </>
      ) : (
        <span>{label}</span>
      )}
    </button>
  );
}
