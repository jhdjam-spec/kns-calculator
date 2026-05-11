"use client";

import { ArrowRight, Phone, FileDown } from "lucide-react";
import type { SelectionResult } from "@/schemas/result";
import { fetchQuestionnaireDocx, fetchEmptyQuestionnaireDocx, triggerDownload } from "@/lib/api";

interface EngineerCTAProps {
  result: SelectionResult | null;
}

/**
 * Inverted CTA-секция в стиле Apple Newsletter:
 * - В light mode → тёмно-teal `bg-brand-900` фон, белый текст. Создаёт «островок»
 *   на фоне светлого hero, привлекает внимание.
 * - В dark mode → остаётся `bg-ink-950` (как в hero), плавно вписан.
 * SVG wireframe-арт всегда виден (низкая opacity), цвет stroke адаптирован.
 */
export function EngineerCTA({ result }: EngineerCTAProps) {
  const handleDownloadDocx = async () => {
    try {
      const blob = result
        ? await fetchQuestionnaireDocx(result, {})
        : await fetchEmptyQuestionnaireDocx();
      triggerDownload(blob, "Опросный_лист_КНС.docx");
    } catch (e) {
      console.error("DOCX download failed:", e);
    }
  };

  return (
    <section
      id="engineer"
      className="py-24 md:py-32 bg-brand-900 dark:bg-ink-950 relative overflow-hidden transition-colors duration-base"
    >
      {/* Background art: large wireframe КНС */}
      <div className="absolute inset-0 flex items-center justify-center opacity-[0.08] dark:opacity-[0.06]">
        <svg
          viewBox="0 0 400 300"
          className="w-full max-w-3xl h-auto"
          stroke="rgba(255,255,255,0.5)"
          strokeWidth="0.75"
          fill="none"
        >
          <ellipse cx="200" cy="100" rx="120" ry="30" />
          <line x1="80" y1="100" x2="80" y2="220" />
          <line x1="320" y1="100" x2="320" y2="220" />
          <ellipse cx="200" cy="220" rx="120" ry="30" />
          <ellipse cx="200" cy="100" rx="120" ry="30" strokeDasharray="3 3" opacity="0.5" />
          <line x1="160" y1="100" x2="160" y2="190" strokeWidth="1.25" />
          <rect x="148" y="190" width="24" height="28" />
          <line x1="240" y1="100" x2="240" y2="190" strokeWidth="1.25" />
          <rect x="228" y="190" width="24" height="28" />
          <path d="M 160 100 L 160 50 L 320 50" />
          <circle cx="320" cy="50" r="4" />
        </svg>
      </div>

      <div className="relative max-w-3xl mx-auto px-5 md:px-10 text-center">
        <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-ink-200 dark:text-ink-300 mb-6">
          <span className="block w-6 h-px bg-accent-500" />
          ИНЖЕНЕР
        </div>
        <h2 className="font-display text-3xl md:text-5xl lg:text-6xl font-semibold text-ink-50 leading-[1.1] tracking-tight">
          Готовы передать данные
          <br />
          <span className="font-normal italic text-accent-500">инженеру?</span>
        </h2>
        <p className="mt-6 text-lg text-ink-200 dark:text-ink-300 max-w-xl mx-auto">
          Получите спецификацию с печатью, расчётом гидравлики и сертификатами за 1 рабочий день.
          Прямой контакт с ведущим инженером — без call-центров.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row gap-3 justify-center">
          <a
            href="tel:+78002224457"
            className="group inline-flex items-center justify-center gap-2 h-14 px-8 rounded-md bg-ink-50 text-ink-950 font-medium hover:bg-accent-500 transition-colors duration-base shadow-premium-lg"
          >
            <Phone size={18} strokeWidth={1.75} />
            <span className="font-mono tabular-nums">8 (800) 222-44-57</span>
            <ArrowRight
              size={16}
              strokeWidth={2}
              className="transition-transform duration-base group-hover:translate-x-1"
            />
          </a>
          <button
            type="button"
            onClick={handleDownloadDocx}
            className="group inline-flex items-center justify-center gap-2 h-14 px-8 rounded-md bg-transparent border border-white/20 text-ink-50 font-medium hover:border-accent-500 hover:text-accent-500 transition-colors duration-base"
          >
            <FileDown size={18} strokeWidth={1.75} />
            Скачать опросный лист
          </button>
        </div>

        <p className="mt-8 text-xs font-mono uppercase tracking-wider text-ink-300 dark:text-ink-500">
          без регистрации · ответ в течение 1 рабочего дня
        </p>
      </div>
    </section>
  );
}
