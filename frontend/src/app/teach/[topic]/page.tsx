// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Энциклопедия инженера ВК                             │
// │ /teach/[topic] — статья по теме (markdown из backend)                 │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Play, ChevronDown } from "lucide-react";
import { useEncyclopediaTopic } from "@/hooks/useProject";
import { MarkdownView } from "@/components/teach/MarkdownView";
import { SiteNav } from "@/components/premium/SiteNav";
import { SiteFooter } from "@/components/premium/SiteFooter";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api/backend";

/** POST на API endpoint примера и возврат JSON-результата. */
async function runExample(endpoint: string, payload: unknown): Promise<unknown> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Backend error ${res.status}: ${text}`);
  }
  return res.json();
}

export default function TeachTopicPage() {
  const params = useParams();
  const topicKey = params.topic as string;
  const { data, isLoading, error } = useEncyclopediaTopic(topicKey);

  return (
    <>
      <SiteNav />
      <main id="main" className="min-h-screen bg-ink-50 dark:bg-ink-950 px-5 md:px-10 pt-24 md:pt-28 pb-10">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8 flex items-center justify-between">
            <a
              href="/teach"
              className="text-sm text-ink-700 dark:text-ink-400 hover:text-brand-700 dark:hover:text-accent-500 transition-colors"
            >
              ← Все темы
            </a>
            <a
              href="/"
              className="text-sm text-ink-600 dark:text-ink-500 hover:text-ink-900 dark:hover:text-ink-200 transition-colors"
            >
              На главную
            </a>
          </div>

          {isLoading && (
            <div className="text-ink-700 dark:text-ink-400 text-center py-20">Загрузка статьи…</div>
          )}

          {error && (
            <div className="p-6 bg-red-50 border border-red-200 dark:bg-red-500/10 dark:border-red-500/30 rounded-md">
              <div className="text-red-700 dark:text-red-400 font-medium">Ошибка загрузки</div>
              <div className="text-red-700 dark:text-red-300 text-sm mt-1">{String(error)}</div>
            </div>
          )}

          {data && (
            <article>
              {/* Нормы, на которых основан раздел */}
              {data.regulations_full && data.regulations_full.length > 0 && (
                <div className="mb-8 p-5 bg-white border border-ink-200 dark:bg-ink-900 dark:border-ink-800 rounded-lg shadow-premium-sm">
                  <div className="text-xs font-mono uppercase tracking-wider text-ink-600 dark:text-ink-500 mb-3">
                    Раздел основан на действующих нормах
                  </div>
                  <ul className="space-y-2">
                    {data.regulations_full.map((r) => (
                      <li key={r.code} className="text-sm leading-snug">
                        <span className="text-brand-700 dark:text-accent-500 font-mono">{r.code}</span>
                        <span className="text-ink-600 dark:text-ink-500"> — </span>
                        <span className="text-ink-700 dark:text-ink-300">{r.name}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Эталонные примеры — наверху, сразу под заголовком */}
              {data.examples.length > 0 && (
                <div className="mb-8 p-5 bg-brand-50 border border-brand-200 dark:bg-accent-500/5 dark:border-accent-500/20 rounded-lg">
                  <div className="text-xs font-mono uppercase tracking-wider text-brand-700 dark:text-accent-500 mb-3">
                    Эталонные примеры
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {data.examples.map((ex) => (
                      <ExampleCard key={ex.id} example={ex} />
                    ))}
                  </div>
                </div>
              )}

              {/* Beta */}
              <div className="mb-6 p-3 bg-yellow-50 border border-yellow-300 dark:bg-yellow-500/5 dark:border-yellow-500/20 rounded text-xs text-yellow-800 dark:text-yellow-300">
                ⚠ Бета-версия. Содержание может уточняться. Перед применением в проекте
                обязательна сверка с актуальной редакцией нормативного документа.
              </div>

              {/* Markdown статьи */}
              <MarkdownView content={data.content_markdown} />
            </article>
          )}
        </div>
      </main>
      <SiteFooter />
    </>
  );
}

interface ExampleData {
  id: string;
  title: string;
  description: string;
  api_endpoint: string;
  payload: Record<string, unknown>;
  expected_outcome: string;
}

/** Карточка эталонного примера с кнопкой «Запустить расчёт» и развёртыванием результата. */
function ExampleCard({ example }: { example: ExampleData }) {
  const [status, setStatus] = useState<"idle" | "running" | "ok" | "error">("idle");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  const handleRun = async () => {
    setStatus("running");
    setError(null);
    try {
      const data = await runExample(example.api_endpoint, example.payload);
      setResult(data);
      setStatus("ok");
      setExpanded(true);
    } catch (e) {
      setError(String(e));
      setStatus("error");
    }
  };

  return (
    <div
      id={example.id}
      className="p-3 bg-white border border-ink-200 dark:bg-ink-900 dark:border-ink-800 rounded-md"
    >
      <div className="font-display font-semibold text-ink-900 dark:text-ink-50 text-sm mb-1">
        {example.title}
      </div>
      <div className="text-xs text-ink-700 dark:text-ink-400 mb-2">{example.description}</div>
      <div className="text-xs text-brand-700 dark:text-accent-300 font-mono mb-3">
        → {example.expected_outcome}
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleRun}
          disabled={status === "running"}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-brand-600 hover:bg-brand-700 disabled:bg-ink-300 disabled:text-ink-500 text-white dark:bg-accent-500 dark:hover:bg-accent-400 dark:disabled:bg-ink-700 dark:text-ink-950 transition-colors"
        >
          <Play size={11} strokeWidth={2.2} />
          {status === "running" ? "Считаем…" : status === "ok" ? "Запустить ещё раз" : "Запустить расчёт"}
        </button>
        {status === "ok" && (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-ink-700 dark:text-ink-400 hover:text-ink-900 dark:hover:text-ink-200 inline-flex items-center gap-1"
          >
            <ChevronDown
              size={12}
              className={expanded ? "rotate-180 transition-transform" : "transition-transform"}
            />
            {expanded ? "Свернуть результат" : "Показать результат"}
          </button>
        )}
      </div>

      {error && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 dark:bg-red-500/10 dark:border-red-500/30 rounded text-xs text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {expanded && result !== null && (
        <pre className="mt-3 p-3 bg-ink-50 border border-ink-200 dark:bg-ink-950 dark:border-ink-800 rounded text-[10px] text-ink-700 dark:text-ink-300 font-mono overflow-x-auto max-h-64">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
