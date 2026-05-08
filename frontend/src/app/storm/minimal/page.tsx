// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
import type { Metadata } from "next";
import { StormMinimalForm } from "@/components/storm/minimal/StormMinimalForm";
import { SiteFooter } from "@/components/premium/SiteFooter";

export const metadata: Metadata = {
  title: "Расчёт ливневой канализации — Минимальный режим · INSERVO",
  description:
    "Калькулятор пикового расхода ливневых вод для парковок, кровель, промплощадок. Бесплатная оценка для бюджета за 1 минуту. Открытый opensource-проект INSERVO Studio.",
};

export default function StormMinimalPage() {
  return (
    <>
      <main className="min-h-screen bg-ink-950 px-5 md:px-10 py-10">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8 flex items-center justify-between">
            <h1 className="text-sm font-mono uppercase tracking-wider text-ink-500">
              INSERVO · Калькулятор ливневок
            </h1>
            <a
              href="/"
              className="text-sm text-ink-400 hover:text-accent-500 transition-colors"
            >
              ← На главную
            </a>
          </div>
          <StormMinimalForm />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
