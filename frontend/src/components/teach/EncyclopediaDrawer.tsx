"use client";

import { useEffect, useState } from "react";
import { X, ExternalLink, BookOpen } from "lucide-react";
import { encyclopediaApi, type EncyclopediaSection } from "@/lib/api-extended";
import { MarkdownView } from "./MarkdownView";

/**
 * Глобальный store для drawer'а (без redux/zustand — простой event bus).
 *
 * Использование из любого места:
 *   import { openEncyclopediaDrawer } from "@/components/teach/EncyclopediaDrawer";
 *   <button onClick={() => openEncyclopediaDrawer({
 *     topic: "fire",
 *     anchor: "Расход на наружное",
 *     valueLabel: "Q_наруж = 15 л/с",
 *   })}>15 л/с</button>
 */

export interface DrawerRequest {
  topic: string;            // "fire" | "hydraulics" | ...
  anchor: string;           // подстрока заголовка (## или ###) для поиска секции
  valueLabel?: string;      // что именно кликнули — для контекста ("Q_наруж = 15 л/с")
  regulation?: string;      // "СП 8.13130 §6.3" — отображается как chip
}

type Listener = (req: DrawerRequest | null) => void;

const listeners: Set<Listener> = new Set();
let currentRequest: DrawerRequest | null = null;

export function openEncyclopediaDrawer(req: DrawerRequest) {
  currentRequest = req;
  listeners.forEach((fn) => fn(req));
}

export function closeEncyclopediaDrawer() {
  currentRequest = null;
  listeners.forEach((fn) => fn(null));
}

function useDrawerRequest(): DrawerRequest | null {
  const [req, setReq] = useState<DrawerRequest | null>(currentRequest);
  useEffect(() => {
    const fn: Listener = (r) => setReq(r);
    listeners.add(fn);
    return () => {
      listeners.delete(fn);
    };
  }, []);
  return req;
}

/** Глобальный drawer — должен быть смонтирован один раз в layout. */
export function EncyclopediaDrawer() {
  const req = useDrawerRequest();
  const [section, setSection] = useState<EncyclopediaSection | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!req) {
      setSection(null);
      setError(null);
      return;
    }
    setIsLoading(true);
    setError(null);
    encyclopediaApi
      .getSection(req.topic, req.anchor)
      .then((s) => setSection(s))
      .catch((e) => setError(String(e)))
      .finally(() => setIsLoading(false));
  }, [req]);

  // Закрытие по Esc
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && req) closeEncyclopediaDrawer();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [req]);

  if (!req) return null;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[60]"
        onClick={closeEncyclopediaDrawer}
        aria-hidden
      />

      {/* Drawer */}
      <aside
        role="dialog"
        aria-label="Справка из энциклопедии"
        className="fixed right-0 top-0 bottom-0 w-full md:w-[640px] lg:w-[720px] bg-ink-950 border-l border-ink-800 z-[70] flex flex-col shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-ink-800 shrink-0">
          <div className="flex items-start gap-3">
            <BookOpen className="text-accent-500 mt-1 shrink-0" size={20} />
            <div>
              <div className="text-xs font-mono uppercase tracking-wider text-ink-500 mb-1">
                Энциклопедия · {req.topic}
              </div>
              <div className="font-display font-semibold text-ink-50">
                {req.valueLabel || req.anchor}
              </div>
              {req.regulation && (
                <div className="mt-1.5 inline-flex items-center gap-1 text-xs px-2 py-0.5 bg-accent-500/10 text-accent-300 rounded font-mono">
                  {req.regulation}
                </div>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={closeEncyclopediaDrawer}
            className="text-ink-400 hover:text-ink-50 transition-colors p-1"
            aria-label="Закрыть"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {isLoading && (
            <div className="text-ink-400 text-sm py-4">Загрузка фрагмента…</div>
          )}

          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded">
              <div className="text-red-400 font-medium text-sm mb-1">Не удалось загрузить</div>
              <div className="text-red-300/80 text-xs">{error}</div>
              <div className="text-ink-400 text-xs mt-3">
                Возможно, фрагмент с заголовком «{req.anchor}» отсутствует в энциклопедии.
                Откройте полную статью →
              </div>
            </div>
          )}

          {section && <MarkdownView content={section.content_markdown} />}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-ink-800 shrink-0 flex items-center justify-between">
          <a
            href={`/teach/${req.topic}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-accent-500 hover:text-accent-400 inline-flex items-center gap-1.5"
          >
            Открыть полную статью
            <ExternalLink size={14} />
          </a>
          <button
            type="button"
            onClick={closeEncyclopediaDrawer}
            className="text-sm text-ink-400 hover:text-ink-50 transition-colors"
          >
            Закрыть (Esc)
          </button>
        </div>
      </aside>
    </>
  );
}

/**
 * Компонент-обёртка над числом/значением, которое разворачивает drawer.
 *
 * Использование:
 *   <ExplainValue topic="fire" anchor="Расход на наружное"
 *                 valueLabel="Q_наруж = 15 л/с" regulation="СП 8.13130 табл.1">
 *     15 л/с
 *   </ExplainValue>
 */
export function ExplainValue({
  children,
  topic,
  anchor,
  valueLabel,
  regulation,
  className = "",
}: {
  children: React.ReactNode;
  topic: string;
  anchor: string;
  valueLabel?: string;
  regulation?: string;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => openEncyclopediaDrawer({ topic, anchor, valueLabel, regulation })}
      className={`inline-flex items-center gap-1 underline decoration-dotted decoration-accent-500/40 underline-offset-4 hover:decoration-accent-500 transition-colors text-left ${className}`}
      title="Открыть справку из энциклопедии"
    >
      {children}
      <BookOpen size={11} className="text-accent-500/60 shrink-0" strokeWidth={1.5} />
    </button>
  );
}
