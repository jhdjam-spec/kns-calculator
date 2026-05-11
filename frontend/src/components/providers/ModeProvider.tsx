"use client";

/**
 * ModeProvider — глобальный контекст «аудитории» интерфейса.
 *
 * Mode != Theme:
 *  - theme  — visual (dark / light / auto) → управляет ThemeToggle.
 *  - mode   — content audience (manager / engineer) → этот провайдер.
 *
 * Идея: один и тот же калькулятор обслуживает две роли — заказчика
 * (менеджер: «расход в м³/ч», цена, срок, упор на УТП и простоту)
 * и проектировщика (инженер: «Q, м³/ч», BEP/η/AOR/zone, формулы СП).
 *
 * Хранение:
 *  - localStorage key `kns_global_mode` (default "manager"); см. ниже.
 *  - sync через `useSyncExternalStore` + storage event между табами
 *    + custom event `kns:global-mode` для синхронизации в одной вкладке
 *    (т.к. storage event не стреляет в том же документе, где была запись).
 *
 * Использование:
 * ```tsx
 * const { mode, setMode, toggle } = useMode();
 * if (mode === "engineer") { ... }
 * ```
 *
 * Backward compat: если компонент не использует `useMode()` — он работает
 * как раньше. Default = manager (массовый пользователь — менеджер заказчика).
 *
 * Sync с SuggestionCard (commit 5ea50ab, key `preferred_suggestion_tab`):
 *  - При смене global mode → пишем тот же tab в SuggestionCard store.
 *  - Если пользователь явно переключит вкладку в SuggestionCard — global
 *    mode НЕ ломаем (направление sync только global → card), чтобы
 *    SuggestionCard оставалась независимой подсказкой ввода.
 *  - Реализовано через эффект внутри ModeProvider, который пишет в
 *    `preferred_suggestion_tab` при изменении global mode.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

export type AppMode = "manager" | "engineer";

export const MODE_STORAGE_KEY = "kns_global_mode";
export const MODE_EVENT = "kns:global-mode";
const DEFAULT_MODE: AppMode = "manager";

// ─── External store (localStorage + event bus) ──────────────────────────

function readMode(): AppMode {
  if (typeof window === "undefined") return DEFAULT_MODE;
  try {
    const v = window.localStorage.getItem(MODE_STORAGE_KEY);
    return v === "engineer" || v === "manager" ? v : DEFAULT_MODE;
  } catch {
    return DEFAULT_MODE;
  }
}

function writeMode(next: AppMode): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(MODE_STORAGE_KEY, next);
    // storage event не стреляет в том же документе → ручной broadcast.
    window.dispatchEvent(new CustomEvent(MODE_EVENT, { detail: next }));
  } catch {
    /* quota / private mode — игнорируем; state останется только в памяти. */
  }
}

function subscribe(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("storage", callback);
  window.addEventListener(MODE_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(MODE_EVENT, callback);
  };
}

// ─── Context ────────────────────────────────────────────────────────────

export interface ModeContextValue {
  mode: AppMode;
  setMode: (next: AppMode) => void;
  toggle: () => void;
}

const ModeContext = createContext<ModeContextValue | null>(null);

export interface ModeProviderProps {
  children: ReactNode;
  /** Принудительный начальный режим (используется в тестах). */
  initialMode?: AppMode;
}

export function ModeProvider({ children, initialMode }: ModeProviderProps) {
  // initialMode применяем один раз при mount — после этого слушаем store.
  useEffect(() => {
    if (initialMode && readMode() !== initialMode) {
      writeMode(initialMode);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const mode = useSyncExternalStore<AppMode>(
    subscribe,
    readMode,
    () => initialMode ?? DEFAULT_MODE, // SSR snapshot
  );

  const setMode = useCallback((next: AppMode) => {
    writeMode(next);
    // Однонаправленная sync с SuggestionCard tab store (ключ
    // `preferred_suggestion_tab`): глобальный режим → подсказки.
    // Обратное направление НЕ синхронизируем намеренно, чтобы
    // SuggestionCard оставалась самостоятельным контролом.
    if (typeof window !== "undefined") {
      try {
        window.localStorage.setItem("preferred_suggestion_tab", next);
        window.dispatchEvent(
          new CustomEvent("kns:suggestion-tab", { detail: next }),
        );
      } catch {
        /* ignore */
      }
    }
  }, []);

  const toggle = useCallback(() => {
    setMode(readMode() === "engineer" ? "manager" : "engineer");
  }, [setMode]);

  const value = useMemo<ModeContextValue>(
    () => ({ mode, setMode, toggle }),
    [mode, setMode, toggle],
  );

  return <ModeContext.Provider value={value}>{children}</ModeContext.Provider>;
}

/**
 * Хук для доступа к глобальному mode.
 *
 * Если провайдер не подключён (например, в standalone-сторибуке или старых
 * страницах) — возвращает безопасный fallback: читает напрямую из localStorage,
 * `setMode` записывает в localStorage, но без broadcast в context. Это нужно
 * чтобы существующие 75 vitest-теста / 41 E2E не падали на missing provider.
 */
export function useMode(): ModeContextValue {
  const ctx = useContext(ModeContext);
  // Fallback hooks — вызываются всегда (rules-of-hooks), но используются
  // только если ctx === null.
  const fallbackMode = useSyncExternalStore<AppMode>(
    subscribe,
    readMode,
    () => DEFAULT_MODE,
  );
  const fallbackSet = useCallback((next: AppMode) => writeMode(next), []);
  const fallbackToggle = useCallback(() => {
    writeMode(readMode() === "engineer" ? "manager" : "engineer");
  }, []);

  if (ctx) return ctx;
  return { mode: fallbackMode, setMode: fallbackSet, toggle: fallbackToggle };
}
