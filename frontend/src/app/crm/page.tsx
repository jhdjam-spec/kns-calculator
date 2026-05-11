// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — CRM-light классификатор входящих писем (P5).         │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// ╰───────────────────────────────────────────────────────────────────────╯
import type { Metadata } from "next";
import { SiteNav } from "@/components/premium/SiteNav";
import { SiteFooter } from "@/components/premium/SiteFooter";
import { ClassifyForm } from "@/components/crm/ClassifyForm";

export const metadata: Metadata = {
  title: "CRM-light: классификатор входящих · INSERVO",
  description:
    "Вставьте текст входящего письма — система определит тип запроса (ОЛ/КП/ТЗ), объект (КНС/ЛОС/ВНС), производителя и извлечёт шифры проектов. P5 mail integration.",
};

export default function CrmPage() {
  return (
    <>
      <SiteNav />
      <main
        id="main"
        className="min-h-screen bg-ink-950 px-5 md:px-10 pt-24 md:pt-28 pb-10"
      >
        <div className="max-w-7xl mx-auto">
          <div className="mb-8 flex items-center justify-between">
            <h1 className="text-sm font-mono uppercase tracking-wider text-ink-500">
              INSERVO · CRM-light классификатор
            </h1>
            <a
              href="/"
              className="text-sm text-ink-400 hover:text-accent-500 transition-colors"
            >
              ← На главную
            </a>
          </div>

          <div className="mb-6">
            <h2 className="text-2xl md:text-3xl font-display font-semibold text-ink-50 mb-2">
              Распознать входящее письмо
            </h2>
            <p className="text-sm text-ink-400 max-w-2xl">
              Вставьте тему и тело письма, добавьте email отправителя — система
              извлечёт тип запроса (ОЛ/КП/ТЗ), объект (КНС/ЛОС/ВНС/…),
              производителя и все шифры проектов. Паттерны обучены на 8 330
              письмах zakaz@inservo.ru (2019–2026).
            </p>
          </div>

          <ClassifyForm />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
