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
      <main className="min-h-screen bg-ink-950 px-5 md:px-10 pt-24 md:pt-28 pb-10">
        <div className="max-w-5xl mx-auto">
          <div className="mb-8 flex items-center justify-between">
            <h1 className="text-sm font-mono uppercase tracking-wider text-ink-500">
              INSERVO · Калькулятор ёмкостей
            </h1>
            <a
              href="/"
              className="text-sm text-ink-400 hover:text-accent-500 transition-colors"
            >
              ← На главную
            </a>
          </div>

          <div className="mb-10 max-w-3xl">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-ink-50 mb-4">
              Расчёт ёмкостей и корпусов КНС
            </h2>
            <p className="text-ink-400 leading-relaxed">
              Расчёт массы, объёма и ориентировочной стоимости горизонтальных
              полипропиленовых (ПП) ёмкостей и вертикальных корпусов{" "}
              <strong className="text-ink-200">КНС</strong> (канализационных насосных станций).
              Формулы основаны на технологическом калькуляторе Серво-Юг.
            </p>
          </div>

          <div role="tablist" className="flex border-b border-ink-800 gap-1 mb-6">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={tab === t.id ? "true" : "false"}
                onClick={() => setTab(t.id)}
                className={clsx(
                  "px-4 py-2 text-sm font-medium border-b-2 transition-colors text-left",
                  tab === t.id
                    ? "border-accent-500 text-accent-500"
                    : "border-transparent text-ink-400 hover:text-ink-200"
                )}
              >
                {t.label}
                <span className="block text-xs font-normal text-ink-500">{t.subtitle}</span>
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
