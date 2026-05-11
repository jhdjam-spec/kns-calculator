// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Энциклопедия инженера ВК                             │
// │ /teach — главная страница: 6 тем + интерактивные примеры              │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { useEncyclopediaTopics, useEncyclopediaExamples } from "@/hooks/useProject";
import { SiteNav } from "@/components/premium/SiteNav";
import { SiteFooter } from "@/components/premium/SiteFooter";

export default function TeachPage() {
  const topics = useEncyclopediaTopics();
  const examples = useEncyclopediaExamples();

  return (
    <>
      <SiteNav />
      <main id="main" className="min-h-screen bg-ink-950 px-5 md:px-10 pt-24 md:pt-28 pb-10">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8 flex items-center justify-between">
            <h1 className="text-sm font-mono uppercase tracking-wider text-ink-500">
              INSERVO · Энциклопедия инженера ВК
            </h1>
            <a
              href="/"
              className="text-sm text-ink-400 hover:text-accent-500 transition-colors"
            >
              ← На главную
            </a>
          </div>

          <div className="mb-12 max-w-3xl">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-ink-50 mb-4">
              Учебник по инженерным расчётам ВК
            </h2>
            <p className="text-ink-400 leading-relaxed">
              6 тематических справочников по гидравлике, пожарной защите, водоснабжению,
              электрике, корпусу и ЛОС. Каждая статья основана на актуальных редакциях
              СП и ГОСТ. Можно запустить эталонные примеры из реальных проектов.
            </p>
          </div>

          {/* 6 топиков */}
          <section className="mb-16">
            <h3 className="text-xs font-mono uppercase tracking-wider text-ink-500 mb-4">
              Тематические разделы
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {topics.isLoading && <div className="text-ink-400">Загрузка тем…</div>}
              {topics.data?.topics.map((t) => (
                <a
                  key={t.key}
                  href={`/teach/${t.key}`}
                  className="flex flex-col p-5 bg-ink-900 border border-ink-800 rounded-lg hover:border-accent-500/50 transition-colors group"
                >
                  <div className="font-display font-semibold text-ink-50 group-hover:text-accent-500 transition-colors mb-2">
                    {t.title}
                  </div>
                  <div className="text-sm text-ink-400 mb-3">{t.short_description}</div>

                  {/* Полные названия норм, на которых основан раздел */}
                  {t.regulations_full && t.regulations_full.length > 0 && (
                    <div className="mt-2 mb-3 pt-3 border-t border-ink-800/60">
                      <div className="text-[10px] font-mono uppercase tracking-wider text-ink-500 mb-2">
                        Основано на нормах
                      </div>
                      <ul className="space-y-1.5">
                        {t.regulations_full.slice(0, 4).map((r) => (
                          <li key={r.code} className="text-xs leading-snug">
                            <span className="text-accent-500/90 font-mono">{r.code}</span>
                            <span className="text-ink-500"> — </span>
                            <span className="text-ink-400">{r.name}</span>
                          </li>
                        ))}
                        {t.regulations_full.length > 4 && (
                          <li className="text-[11px] text-ink-500 italic">
                            и ещё {t.regulations_full.length - 4} ↗
                          </li>
                        )}
                      </ul>
                    </div>
                  )}

                  <div className="mt-auto text-xs font-mono text-ink-500">
                    {t.sections_count} разделов
                  </div>
                </a>
              ))}
            </div>
          </section>

          {/* Эталонные примеры */}
          <section>
            <h3 className="text-xs font-mono uppercase tracking-wider text-ink-500 mb-4">
              Эталонные примеры из реальных проектов
            </h3>
            <p className="text-ink-400 text-sm mb-6">
              Каждый пример запускает калькулятор с реальными параметрами.
              Используйте для сравнения и обучения.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {examples.isLoading && <div className="text-ink-400">Загрузка примеров…</div>}
              {examples.data?.examples.map((ex) => (
                <a
                  key={ex.id}
                  href={`/teach/${ex.topic}#${ex.id}`}
                  className="block p-4 bg-ink-900 border border-ink-800 rounded-lg hover:border-ink-600 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className="text-2xl">📐</div>
                    <div className="flex-1">
                      <div className="font-display font-semibold text-ink-100 mb-1">
                        {ex.title}
                      </div>
                      <div className="text-sm text-ink-400 mb-2">{ex.description}</div>
                      <div className="text-xs text-accent-500 font-mono">
                        Ожидается: {ex.expected_outcome}
                      </div>
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </section>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
