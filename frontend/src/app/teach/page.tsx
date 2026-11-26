// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Энциклопедия инженера ВК                             │
// │ /teach — главная страница: 6 тем + интерактивные примеры              │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { useEncyclopediaTopics, useEncyclopediaExamples } from "@/hooks/useProject";
import { SiteNav } from "@/components/premium/SiteNav";
import { SiteFooter } from "@/components/premium/SiteFooter";
import { TeachLink } from "@/components/TeachLink";

export default function TeachPage() {
  const topics = useEncyclopediaTopics();
  const examples = useEncyclopediaExamples();

  return (
    <>
      <SiteNav />
      <main id="main" className="kns-document min-h-screen bg-ink-50 dark:bg-ink-950 px-5 md:px-10 pt-24 md:pt-28 pb-10">
        <div className="max-w-7xl mx-auto">
          <div className="mb-12 flex items-center justify-between">
            <a
              href="/"
              className="text-sm text-ink-700 dark:text-ink-400 hover:text-clover-700 dark:hover:text-clover-300 transition-colors"
            >
              ← На главную
            </a>
          </div>

          <div className="mb-14 max-w-3xl">
            <h1 className="font-display text-[2.5rem] sm:text-5xl md:text-6xl lg:text-7xl font-medium text-ink-900 dark:text-ink-50 leading-[0.95] tracking-[-0.04em] mb-6">
              Справочник по{" "}
              <span className="font-normal italic font-serif text-clover-700 dark:text-clover-300">
                СП и ГОСТ
              </span>
              <span className="text-ink-400 dark:text-ink-500">.</span>
            </h1>
            <p className="text-lg md:text-xl text-ink-700 dark:text-ink-300 leading-relaxed max-w-2xl">
              7 разделов: гидравлика, пожарная защита, водоснабжение, электрика,
              конструктив, ЛОС, документация. Каждая статья — с цитатами из
              актуальных редакций нормативов и ссылками на cntd.ru.
            </p>
          </div>

          {/* 6 топиков */}
          <section className="mb-16">
            <h2 className="text-xs font-mono uppercase tracking-wider text-ink-600 dark:text-ink-500 mb-4">
              Тематические разделы
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {topics.isLoading && <div className="text-ink-700 dark:text-ink-400">Загрузка тем…</div>}
              {topics.data?.topics.map((t) => (
                <TeachLink
                  key={t.key}
                  href={`/teach/${t.key}`}
                  className="flex flex-col p-5 bg-white border border-ink-200 dark:bg-ink-900 dark:border-ink-800 rounded-lg hover:border-brand-400 dark:hover:border-accent-500/50 transition-colors group shadow-premium-sm"
                >
                  <div className="font-display font-semibold text-ink-900 dark:text-ink-50 group-hover:text-brand-700 dark:group-hover:text-accent-500 transition-colors mb-2">
                    {t.title}
                  </div>
                  <div className="text-sm text-ink-700 dark:text-ink-400 mb-3">{t.short_description}</div>

                  {/* Полные названия норм, на которых основан раздел */}
                  {t.regulations_full && t.regulations_full.length > 0 && (
                    <div className="mt-2 mb-3 pt-3 border-t border-ink-200 dark:border-ink-800/60">
                      <div className="text-[10px] font-mono uppercase tracking-wider text-ink-600 dark:text-ink-500 mb-2">
                        Основано на нормах
                      </div>
                      <ul className="space-y-1.5">
                        {t.regulations_full.slice(0, 4).map((r) => (
                          <li key={r.code} className="text-xs leading-snug">
                            <span className="text-brand-700 dark:text-accent-500/90 font-mono">{r.code}</span>
                            <span className="text-ink-600 dark:text-ink-500"> — </span>
                            <span className="text-ink-700 dark:text-ink-400">{r.name}</span>
                          </li>
                        ))}
                        {t.regulations_full.length > 4 && (
                          <li className="text-[11px] text-ink-600 dark:text-ink-500 italic">
                            и ещё {t.regulations_full.length - 4} ↗
                          </li>
                        )}
                      </ul>
                    </div>
                  )}

                  <div className="mt-auto text-xs font-mono text-ink-600 dark:text-ink-500">
                    {t.sections_count} разделов
                  </div>
                </TeachLink>
              ))}
            </div>
          </section>

          {/* Failure Mode Library — отдельная карточка */}
          <section className="mb-16">
            <TeachLink
              href="/teach/failure-modes"
              className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-5 bg-white border border-ink-200 dark:bg-ink-900 dark:border-ink-800 rounded-lg hover:border-brand-400 dark:hover:border-accent-500/50 transition-colors group shadow-premium-sm"
            >
              <div>
                <div className="font-display font-semibold text-ink-900 dark:text-ink-50 group-hover:text-brand-700 dark:group-hover:text-accent-500 transition-colors mb-1">
                  📚 Библиотека типовых отказов
                </div>
                <div className="text-sm text-ink-700 dark:text-ink-400">
                  26 режимов отказа КНС/НС: симптомы · причины · профилактика · стоимость ремонта · downtime.
                </div>
              </div>
              <span className="text-brand-700 dark:text-accent-500 group-hover:translate-x-1 transition-transform">→</span>
            </TeachLink>
          </section>

          {/* Эталонные примеры */}
          <section>
            <h2 className="text-xs font-mono uppercase tracking-wider text-ink-600 dark:text-ink-500 mb-4">
              Эталонные примеры из реальных проектов
            </h2>
            <p className="text-ink-700 dark:text-ink-400 text-sm mb-6">
              Каждый пример запускает калькулятор с реальными параметрами.
              Используйте для сравнения и обучения.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {examples.isLoading && <div className="text-ink-700 dark:text-ink-400">Загрузка примеров…</div>}
              {examples.data?.examples.map((ex) => (
                <a
                  key={ex.id}
                  href={`/teach/${ex.topic}#${ex.id}`}
                  className="block p-4 bg-white border border-ink-200 dark:bg-ink-900 dark:border-ink-800 rounded-lg hover:border-brand-400 dark:hover:border-ink-600 transition-colors shadow-premium-sm"
                >
                  <div className="flex items-start gap-3">
                    <div className="text-2xl">📐</div>
                    <div className="flex-1">
                      <div className="font-display font-semibold text-ink-900 dark:text-ink-100 mb-1">
                        {ex.title}
                      </div>
                      <div className="text-sm text-ink-700 dark:text-ink-400 mb-2">{ex.description}</div>
                      <div className="text-xs text-brand-700 dark:text-accent-500 font-mono">
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
