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
  title: "Импорт ТЗ — автоподбор насоса по тексту задания · Серво-Юг",
  description:
    "Вставьте текст ТЗ или опросного листа — калькулятор извлечёт Q, H, город, тип стоков. Данные подставятся в мастер проекта автоматически.",
  alternates: { canonical: "/import" },
  openGraph: {
    title: "Импорт ТЗ — автоподбор насоса по тексту задания · Серво-Юг",
    description:
      "Вставьте текст ТЗ — калькулятор извлечёт Q, H, город, тип стоков и подставит в мастер проекта.",
    url: "/import",
    type: "website",
  },
};

export default function ImportPage() {
  return (
    <>
      <SiteNav />
      <main
        id="main"
        className="kns-document min-h-screen bg-ink-50 px-5 md:px-10 pt-24 md:pt-28 pb-10"
      >
        <div className="max-w-7xl mx-auto">
          <div className="mb-12 flex items-center justify-between">
            <a
              href="/"
              className="text-sm text-ink-700 hover:text-clover-700 transition-colors"
            >
              ← На главную
            </a>
          </div>

          <div className="mb-14 max-w-3xl">
            <h1 className="font-display text-[2.5rem] sm:text-5xl md:text-6xl lg:text-7xl font-medium text-ink-900 leading-[0.95] tracking-[-0.04em] mb-6">
              Вставьте{" "}
              <span className="font-normal italic font-serif text-clover-700">
                ТЗ
              </span>{" "}
              — получите подбор
            </h1>
            <p className="text-lg md:text-xl text-ink-700 leading-relaxed max-w-2xl">
              PDF / DOCX / email / текст — извлекаем Q, H, город, тип стоков,
              шифр проекта и требования (ATEX, категория надёжности). Дальше — полный
              проект или быстрый подбор по Q/H.
            </p>
          </div>

          <TZImportForm />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
