// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — TZ Import page (Phase 33).                           │
// │ Вставьте ТЗ → backend парсит Q/H/город/тип → pre-fill wizard L0/L1.   │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// ╰───────────────────────────────────────────────────────────────────────╯
import type { Metadata } from "next";
import { SiteNav } from "@/components/premium/SiteNav";
import { SiteFooter } from "@/components/premium/SiteFooter";
import { TZImportForm } from "@/components/import_tz/TZImportForm";

export const metadata: Metadata = {
  title: "Импорт ТЗ — автоподбор оборудования · INSERVO",
  description:
    "Вставьте текст технического задания или опросного листа — калькулятор извлечёт расход Q, напор H, город, тип стоков и шифр проекта. Данные подставятся в мастер проекта автоматически.",
};

export default function ImportPage() {
  return (
    <>
      <SiteNav />
      <main
        id="main"
        className="min-h-screen bg-ink-50 px-5 md:px-10 pt-24 md:pt-28 pb-10"
      >
        <div className="max-w-7xl mx-auto">
          <div className="mb-8 flex items-center justify-between">
            <h1 className="text-sm font-mono uppercase tracking-wider text-ink-600">
              INSERVO · Импорт ТЗ
            </h1>
            <a
              href="/"
              className="text-sm text-ink-700 hover:text-brand-700 transition-colors"
            >
              ← На главную
            </a>
          </div>

          <div className="mb-6">
            <h2 className="text-2xl md:text-3xl font-display font-semibold text-ink-900 mb-2">
              Вставьте ТЗ — система подберёт оборудование
            </h2>
            <p className="text-sm text-ink-700 max-w-2xl">
              Менеджер получает ТЗ от клиента (PDF/DOCX/email/текст), копирует
              в форму — калькулятор извлекает расход, напор, город, тип стоков,
              шифр проекта и сопутствующие требования (ATEX, категория
              надёжности, температура). Дальше — «Создать полный проект»
              (мастер L0+L1 заполнится автоматически) или «Быстрый подбор»
              (топ-3 насоса по Q/H).
            </p>
          </div>

          <TZImportForm />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
