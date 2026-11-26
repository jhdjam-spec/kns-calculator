"use client";

import { useState } from "react";
import clsx from "clsx";
import { HorizontalTankForm } from "@/components/HorizontalTankForm";
import { KnsCorpusForm } from "@/components/KnsCorpusForm";
import { SiteNav } from "@/components/premium/SiteNav";
import { SiteFooter } from "@/components/premium/SiteFooter";

type Tab = "pp" | "fiberglass" | "kns";

const TABS: { id: Tab; label: string; subtitle: string }[] = [
  { id: "pp", label: "ПП-ёмкости", subtitle: "Горизонтальные, полипропилен" },
  { id: "kns", label: "Корпус КНС", subtitle: "Вертикальный ПП" },
  { id: "fiberglass", label: "Стеклопластик", subtitle: "В разработке" },
];

export default function TanksPage() {
  const [tab, setTab] = useState<Tab>("pp");

  return (
    <>
      <SiteNav />
      <main id="main" className="kns-document min-h-screen bg-ink-50 dark:bg-ink-950 px-5 md:px-10 pt-24 md:pt-28 pb-10">
        <div className="max-w-5xl mx-auto">
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
              Расчёт{" "}
              <span className="font-normal italic font-serif text-clover-700 dark:text-clover-300">
                ёмкостей
              </span>{" "}
              и корпусов КНС
            </h1>
            <p className="text-lg md:text-xl text-ink-700 dark:text-ink-300 leading-relaxed max-w-2xl">
              Масса, объём и ориентировочная стоимость горизонтальных ПП-ёмкостей
              и вертикальных корпусов КНС. Плюс прочностной расчёт по СП 22.
            </p>
          </div>

          {/* Tabs. На mobile-узких экранах subtitle скрыт, контейнер horizontal-scroll
              если не вмещается. На md+ — нормальный flex с подзаголовками. */}
          <div role="tablist" className="flex border-b border-ink-200 dark:border-ink-800 gap-1 mb-6 overflow-x-auto -mx-1 px-1">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={tab === t.id ? "true" : "false"}
                onClick={() => setTab(t.id)}
                className={clsx(
                  "shrink-0 px-3 sm:px-4 py-2 text-sm font-medium border-b-2 transition-colors text-left whitespace-nowrap",
                  tab === t.id
                    ? "border-brand-600 text-brand-700 dark:border-accent-500 dark:text-accent-500"
                    : "border-transparent text-ink-700 dark:text-ink-400 hover:text-ink-900 dark:hover:text-ink-200"
                )}
              >
                {t.label}
                <span className="hidden sm:block text-xs font-normal text-ink-600 dark:text-ink-500">{t.subtitle}</span>
              </button>
            ))}
          </div>

          <section className="bg-ink-50 border border-ink-200 rounded-lg p-6 text-ink-950">
            {tab === "pp" && <HorizontalTankForm />}
            {tab === "kns" && <KnsCorpusForm />}
            {tab === "fiberglass" && (
              <div className="rounded-lg border-2 border-dashed border-ink-300 p-8 text-center">
                <h3 className="text-lg font-display font-semibold text-ink-950 mb-2">
                  Калькулятор стеклопластиковых ёмкостей
                </h3>
                <p className="text-ink-600 max-w-lg mx-auto leading-relaxed">
                  В разработке. Использует ту же геометрию, что и ПП-калькулятор,
                  но с другими параметрами материала: плотность стеклопластика
                  1700–2000 кг/м³ (vs ~920 кг/м³ для ПП), удельная цена выше в 1.5–2 раза.
                </p>
                <p className="text-sm text-ink-500 mt-4">
                  Появится в следующих обновлениях.
                </p>
              </div>
            )}
          </section>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
