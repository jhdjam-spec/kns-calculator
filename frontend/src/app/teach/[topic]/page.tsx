// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Энциклопедия инженера ВК                             │
// │ /teach/[topic] — статья по теме (markdown из backend)                 │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { useParams } from "next/navigation";
import { useEncyclopediaTopic } from "@/hooks/useProject";
import { MarkdownView } from "@/components/teach/MarkdownView";
import { SiteFooter } from "@/components/premium/SiteFooter";

export default function TeachTopicPage() {
  const params = useParams();
  const topicKey = params.topic as string;
  const { data, isLoading, error } = useEncyclopediaTopic(topicKey);

  return (
    <>
      <main className="min-h-screen bg-ink-950 px-5 md:px-10 py-10">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8 flex items-center justify-between">
            <a
              href="/teach"
              className="text-sm text-ink-400 hover:text-accent-500 transition-colors"
            >
              ← Все темы
            </a>
            <a
              href="/"
              className="text-sm text-ink-500 hover:text-ink-200 transition-colors"
            >
              На главную
            </a>
          </div>

          {isLoading && (
            <div className="text-ink-400 text-center py-20">Загрузка статьи…</div>
          )}

          {error && (
            <div className="p-6 bg-red-500/10 border border-red-500/30 rounded-md">
              <div className="text-red-400 font-medium">Ошибка загрузки</div>
              <div className="text-red-300 text-sm mt-1">{String(error)}</div>
            </div>
          )}

          {data && (
            <article>
              {/* Эталонные примеры — наверху, сразу под заголовком */}
              {data.examples.length > 0 && (
                <div className="mb-8 p-5 bg-accent-500/5 border border-accent-500/20 rounded-lg">
                  <div className="text-xs font-mono uppercase tracking-wider text-accent-500 mb-3">
                    Эталонные примеры
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {data.examples.map((ex) => (
                      <div
                        key={ex.id}
                        id={ex.id}
                        className="p-3 bg-ink-900 border border-ink-800 rounded-md"
                      >
                        <div className="font-display font-semibold text-ink-50 text-sm mb-1">
                          {ex.title}
                        </div>
                        <div className="text-xs text-ink-400 mb-2">{ex.description}</div>
                        <div className="text-xs text-accent-300 font-mono">
                          → {ex.expected_outcome}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Beta */}
              <div className="mb-6 p-3 bg-yellow-500/5 border border-yellow-500/20 rounded text-xs text-yellow-300">
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
