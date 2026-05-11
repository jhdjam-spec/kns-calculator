"use client";

/**
 * SuggestionCard — карточка для одной `InputSuggestion` от backend.
 *
 * Бэкенд (commit 2beab6a) отдаёт два варианта объяснения одной и той же
 * рекомендации: `reason_engineer` (язык инженера-проектировщика) и
 * `reason_manager` (язык менеджера/заказчика). Старое поле `reason` —
 * fallback для backward compatibility если бэкенд ещё не задеплоен.
 *
 * Стек: Tailwind + headless (без shadcn/Radix) — см.
 * `reference_kns_brand_audit_2026-05-11.md`.
 *
 * Дизайн: два визуальных варианта.
 *  - variant="light" — для премиум-страницы (ResultsCompare, bg-ink-50).
 *  - variant="dark"  — для wizard'а (ProjectStepResults, bg-ink-950).
 *
 * Выбор активной вкладки сохраняется в `localStorage` под ключом
 * `preferred_suggestion_tab`, чтобы при переключении в одной карточке
 * все остальные карточки на странице (и на других страницах) тоже
 * мгновенно переключались.
 */

import { useEffect, useState, useCallback, useSyncExternalStore } from "react";
import clsx from "clsx";
import type { InputSuggestion } from "@/schemas/result";

export type SuggestionTab = "manager" | "engineer";

const LS_KEY = "preferred_suggestion_tab";
const DEFAULT_TAB: SuggestionTab = "manager";

// ─── Глобальный store вкладки (sync через localStorage + custom event) ────

function readTab(): SuggestionTab {
  if (typeof window === "undefined") return DEFAULT_TAB;
  try {
    const v = window.localStorage.getItem(LS_KEY);
    return v === "engineer" || v === "manager" ? v : DEFAULT_TAB;
  } catch {
    return DEFAULT_TAB;
  }
}

function writeTab(next: SuggestionTab): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LS_KEY, next);
    // Уведомляем подписчиков на этой же вкладке браузера
    // (storage event не стреляет в том же документе, где была запись).
    window.dispatchEvent(new CustomEvent("kns:suggestion-tab", { detail: next }));
  } catch {
    /* quota / private mode — игнорируем, состояние останется только в памяти */
  }
}

function subscribe(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("storage", callback);
  window.addEventListener("kns:suggestion-tab", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("kns:suggestion-tab", callback);
  };
}

/**
 * Хук — текущая активная вкладка с авто-синхронизацией.
 * Использует `useSyncExternalStore` чтобы все экземпляры SuggestionCard
 * на странице переключались одновременно.
 */
export function useSuggestionTab(): [SuggestionTab, (next: SuggestionTab) => void] {
  const tab = useSyncExternalStore(
    subscribe,
    readTab,
    () => DEFAULT_TAB, // SSR snapshot
  );
  const setTab = useCallback((next: SuggestionTab) => writeTab(next), []);
  return [tab, setTab];
}

// ─── Локализация полей и severity ───────────────────────────────────────

/** Маппинг технического имени поля backend → человекочитаемое название. */
const FIELD_LABELS: Record<string, string> = {
  Q_m3h: "Расход Q, м³/ч",
  dH_m: "Перепад dH, м",
  H_geo_m: "Геодезический напор, м",
  T_C: "Температура, °C",
  L_m: "Длина трассы L, м",
  inflow_m3h: "Приток, м³/ч",
  "L1.pipe_D_mm": "Диаметр трубы, мм",
  "L1.pipe_material": "Материал трубы",
  "L1.pipe_length_m": "Длина трубы, м",
};

function localizeField(field: string): string {
  return FIELD_LABELS[field] || field;
}

const SEVERITY_META = {
  critical: {
    label: "Обязательно проверьте",
    dotClass: "bg-red-500",
    badgeLight: "bg-red-50 text-red-700 border-red-200",
    badgeDark: "bg-red-500/10 text-red-300 border-red-500/30",
    icon: "!",
  },
  warning: {
    label: "Рекомендуем проверить",
    dotClass: "bg-yellow-500",
    badgeLight: "bg-yellow-50 text-yellow-800 border-yellow-200",
    badgeDark: "bg-yellow-500/10 text-yellow-300 border-yellow-500/30",
    icon: "▲",
  },
  info: {
    label: "Информация",
    dotClass: "bg-blue-500",
    badgeLight: "bg-blue-50 text-blue-700 border-blue-200",
    badgeDark: "bg-blue-500/10 text-blue-300 border-blue-500/30",
    icon: "i",
  },
} as const;

// ─── Component ──────────────────────────────────────────────────────────

export interface SuggestionCardProps {
  suggestion: InputSuggestion;
  /** Принудительно установить вкладку (по умолчанию — глобальный store). */
  defaultTab?: SuggestionTab;
  /** Тема. light — для premium-страницы, dark — для wizard. */
  variant?: "light" | "dark";
  className?: string;
}

export function SuggestionCard({
  suggestion,
  defaultTab,
  variant = "light",
  className,
}: SuggestionCardProps) {
  const [globalTab, setGlobalTab] = useSuggestionTab();
  // Если передан defaultTab — берём localStorage только при mount,
  // потом всё равно слушаем глобальный store.
  const [didInit, setDidInit] = useState(false);
  useEffect(() => {
    if (!didInit && defaultTab && readTab() !== defaultTab) {
      setGlobalTab(defaultTab);
    }
    setDidInit(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activeTab = globalTab;
  const sev = SEVERITY_META[suggestion.severity] ?? SEVERITY_META.info;
  const reasonEng = suggestion.reason_engineer?.trim() || "";
  const reasonMgr = suggestion.reason_manager?.trim() || "";
  const fallback = suggestion.reason?.trim() || "";

  // Фактически отображаемый текст:
  //  - предпочитаем reason_engineer/reason_manager
  //  - fallback к reason (старый backend без расширенных полей)
  let bodyText = "";
  if (activeTab === "engineer") {
    bodyText = reasonEng || fallback || reasonMgr;
  } else {
    bodyText = reasonMgr || fallback || reasonEng;
  }

  // Если backend отдаёт оба новых поля — показываем toggle. Иначе скрываем.
  const showToggle = Boolean(reasonEng && reasonMgr);

  const isDark = variant === "dark";

  return (
    <div
      data-testid="suggestion-card"
      data-severity={suggestion.severity}
      className={clsx(
        "rounded-card border p-4 md:p-5",
        isDark
          ? "bg-ink-900 border-ink-800 text-ink-100"
          : "bg-white border-ink-200 text-ink-900",
        className,
      )}
    >
      {/* Header: severity badge + поле */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span
          className={clsx(
            "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider border",
            isDark ? sev.badgeDark : sev.badgeLight,
          )}
        >
          <span
            aria-hidden="true"
            className={clsx("inline-block w-1.5 h-1.5 rounded-full", sev.dotClass)}
          />
          {sev.label}
        </span>
        <span
          className={clsx(
            "text-xs font-mono uppercase tracking-wider",
            isDark ? "text-ink-400" : "text-ink-500",
          )}
        >
          {localizeField(suggestion.field)}
        </span>
      </div>

      {/* Value diff */}
      <div className="flex flex-wrap items-baseline gap-2 mb-3">
        <span
          className={clsx(
            "font-mono tabular-nums text-sm line-through",
            isDark ? "text-ink-500" : "text-ink-500",
          )}
        >
          {suggestion.current_value}
        </span>
        <span
          aria-hidden="true"
          className={clsx("text-sm", isDark ? "text-ink-400" : "text-ink-400")}
        >
          →
        </span>
        <span
          className={clsx(
            "font-mono tabular-nums text-base font-semibold",
            isDark ? "text-accent-400" : "text-accent-600",
          )}
        >
          {suggestion.suggested_value}
        </span>
      </div>

      {/* Tab toggle */}
      {showToggle && (
        <div
          role="tablist"
          aria-label="Уровень объяснения"
          className={clsx(
            "inline-flex rounded-md p-0.5 mb-3 border",
            isDark
              ? "bg-ink-950 border-ink-800"
              : "bg-ink-100 border-ink-200",
          )}
        >
          <TabButton
            isDark={isDark}
            isActive={activeTab === "manager"}
            onClick={() => setGlobalTab("manager")}
            controls="suggestion-body"
          >
            Менеджер
          </TabButton>
          <TabButton
            isDark={isDark}
            isActive={activeTab === "engineer"}
            onClick={() => setGlobalTab("engineer")}
            controls="suggestion-body"
          >
            Инженер
          </TabButton>
        </div>
      )}

      {/* Body */}
      <p
        id="suggestion-body"
        role="tabpanel"
        className={clsx(
          "text-sm leading-relaxed",
          isDark ? "text-ink-200" : "text-ink-700",
        )}
      >
        {bodyText || "—"}
      </p>
    </div>
  );
}

interface TabButtonProps {
  isDark: boolean;
  isActive: boolean;
  onClick: () => void;
  controls: string;
  children: React.ReactNode;
}

function TabButton({ isDark, isActive, onClick, controls, children }: TabButtonProps) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={isActive}
      aria-controls={controls}
      onClick={onClick}
      className={clsx(
        "px-3 py-1 rounded text-xs font-medium transition-colors min-h-[32px]",
        isActive
          ? isDark
            ? "bg-ink-800 text-ink-50 shadow-sm"
            : "bg-white text-ink-950 shadow-sm"
          : isDark
            ? "text-ink-400 hover:text-ink-100"
            : "text-ink-500 hover:text-ink-900",
      )}
    >
      {children}
    </button>
  );
}

/** Список карточек с заголовком — удобно для встраивания на странице. */
export function SuggestionList({
  suggestions,
  variant = "light",
  title = "Возможно вы имели в виду",
}: {
  suggestions: InputSuggestion[];
  variant?: "light" | "dark";
  title?: string;
}) {
  if (!suggestions || suggestions.length === 0) return null;
  const isDark = variant === "dark";
  return (
    <section
      aria-label="Предложения по уточнению ввода"
      className={clsx(
        "rounded-card border p-4 md:p-5",
        isDark
          ? "bg-ink-950 border-ink-800"
          : "bg-ink-50 border-ink-200",
      )}
    >
      <div
        className={clsx(
          "text-xs font-mono uppercase tracking-wider mb-3",
          isDark ? "text-ink-400" : "text-ink-500",
        )}
      >
        {title} · {suggestions.length}
      </div>
      <div className="grid grid-cols-1 gap-3">
        {suggestions.map((s, i) => (
          <SuggestionCard
            key={`${s.field}-${i}`}
            suggestion={s}
            variant={variant}
          />
        ))}
      </div>
    </section>
  );
}
