// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
import type { Metadata } from "next";
import { StormMinimalForm } from "@/components/storm/minimal/StormMinimalForm";
import { SiteNav } from "@/components/premium/SiteNav";
import { SiteFooter } from "@/components/premium/SiteFooter";

export const metadata: Metadata = {
  title: "Расчёт ливневой канализации онлайн — пиковый расход · Серво-Юг",
  description:
    "Калькулятор пикового расхода ливневых вод для парковок, кровель, промплощадок по СП 32.13330. Бесплатная оценка для бюджета за 1 минуту.",
  alternates: { canonical: "/storm/minimal" },
  openGraph: {
    title: "Расчёт ливневой канализации онлайн · Серво-Юг",
    description:
      "Пиковый расход ливневых вод по СП 32.13330 за 1 минуту. Парковки, кровли, промплощадки.",
    url: "/storm/minimal",
    type: "website",
  },
};

export default function StormMinimalPage() {
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
              Расчёт{" "}
              <span className="font-normal italic font-serif text-clover-700 dark:text-clover-300">
                ливнёвки
              </span>{" "}
              по СП 32
            </h1>
            <p className="text-lg md:text-xl text-ink-700 dark:text-ink-300 leading-relaxed max-w-2xl">
              Пиковый расход, объём аккумулятора, диаметр труб — за минуту.
              База 36 городов СП 131.
            </p>
          </div>
          <StormMinimalForm />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
