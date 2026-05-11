// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Проект: единый визард всех расчётов (Phase 22-32)                     │
// ╰───────────────────────────────────────────────────────────────────────╯
import type { Metadata } from "next";
import { ProjectWizard } from "@/components/project/ProjectWizard";
import { SiteNav } from "@/components/premium/SiteNav";
import { SiteFooter } from "@/components/premium/SiteFooter";

export const metadata: Metadata = {
  title: "Проект — Главный режим · INSERVO",
  description:
    "Единый визард проекта: вы вводите тип объекта и базовые параметры — калькулятор автоматически прогоняет все нужные расчёты (КНС, ВНС, пожарка, ЛОС, электрика, климат, прочность) и собирает сводку. Бета-версия INSERVO Studio.",
};

export default function ProjectPage() {
  return (
    <>
      <SiteNav />
      <main id="main" className="min-h-screen bg-ink-50 dark:bg-ink-950 px-5 md:px-10 pt-24 md:pt-28 pb-10">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8 flex items-center justify-between">
            <h1 className="text-sm font-mono uppercase tracking-wider text-ink-600 dark:text-ink-500">
              INSERVO · Проект целиком
            </h1>
            <a
              href="/"
              className="text-sm text-ink-600 dark:text-ink-400 hover:text-brand-700 dark:hover:text-accent-500 transition-colors"
            >
              ← На главную
            </a>
          </div>
          <div className="mb-10 max-w-3xl">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-ink-900 dark:text-ink-50 mb-4">
              Один проект — все расчёты
            </h2>
            <p className="text-ink-700 dark:text-ink-400 leading-relaxed">
              Выберите тип объекта, введите базовые параметры — и калькулятор автоматически
              прогонит расчёты по всем подсистемам: КНС, ВНС хозпит. и пожарную, ливнёвку,
              ЛОС, электрику, климат и прочность. Результат — сводка с ссылками на нормативы
              СП 32, СП 8.13130, СП 30/31, СП 131, ПУЭ и другие.
            </p>
          </div>
          <ProjectWizard />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
