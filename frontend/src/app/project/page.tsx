// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Проект: единый визард всех расчётов (Phase 22-32)                     │
// ╰───────────────────────────────────────────────────────────────────────╯
import type { Metadata } from "next";
import { ProjectWizard } from "@/components/project/ProjectWizard";
import { SiteNav } from "@/components/premium/SiteNav";
import { SiteFooter } from "@/components/premium/SiteFooter";

export const metadata: Metadata = {
  title: "Проект целиком — расчёт всех подсистем · Серво-Юг",
  description:
    "Единый визард: КНС, ВНС, пожарная, ливнёвка, ЛОС, электрика, климат, прочность. Результат — сводка со ссылками на СП и ГОСТ. Бесплатно.",
  alternates: { canonical: "/project" },
  openGraph: {
    title: "Проект целиком — расчёт всех подсистем · Серво-Юг",
    description:
      "Единый визард: КНС, ВНС, пожарная, ливнёвка, ЛОС, электрика, климат, прочность. Сводка со ссылками на СП и ГОСТ.",
    url: "/project",
    type: "website",
  },
};

export default function ProjectPage() {
  return (
    <>
      <SiteNav />
      <main id="main" className="kns-document min-h-screen bg-ink-50 dark:bg-ink-950 px-5 md:px-10 pt-24 md:pt-28 pb-10">
        <div className="max-w-7xl mx-auto">
          <div className="mb-12 flex items-center justify-between">
            <a
              href="/"
              className="text-sm text-ink-600 dark:text-ink-400 hover:text-clover-700 dark:hover:text-clover-300 transition-colors"
            >
              ← На главную
            </a>
          </div>
          <div className="mb-12 max-w-3xl">
            <h1 className="font-display text-[2.5rem] sm:text-5xl md:text-6xl lg:text-7xl font-medium text-ink-900 dark:text-ink-50 leading-[0.95] tracking-[-0.04em] mb-6">
              Один проект —{" "}
              <span className="font-normal italic font-serif text-clover-700 dark:text-clover-300">
                все
              </span>{" "}
              расчёты
            </h1>
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
