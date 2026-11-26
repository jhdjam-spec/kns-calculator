"use client";

import { useState } from "react";
import { Plus, Minus } from "lucide-react";
import clsx from "clsx";

const faqs = [
  {
    q: "Что вводить, если знаю только расход?",
    a: "Укажите расход в м³/ч в форме быстрого подбора. Подставленные параметры будут перечислены в результатах.",
  },
  {
    q: "Как уточнить расчёт?",
    a: "В расширенной форме можно указать перепад высот, длину и диаметр напорной трубы. Если расход неизвестен, откройте помощник рядом с полем расхода.",
  },
  {
    q: "Можно ли использовать результат для заказа?",
    a: "По результатам можно сравнить модели и оценить бюджет. Перед заказом передайте исходные данные инженеру для проверки.",
  },
  {
    q: "Где скачать опросный лист?",
    a: "Пустой бланк доступен на первом экране. После расчёта можно скачать лист с данными подбора.",
  },
];

export function FAQ() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section id="faq" className="py-12 md:py-16 bg-background border-t border-border">
      <div className="max-w-3xl mx-auto px-5 md:px-10">
        <div className="mb-5">
          <h2 className="font-display text-2xl md:text-3xl font-semibold text-foreground leading-tight tracking-tight">
            Частые вопросы
          </h2>
        </div>

        <div>
          {faqs.map((item, i) => {
            const isOpen = open === i;
            const panelId = `faq-panel-${i}`;
            const triggerId = `faq-trigger-${i}`;
            return (
              <div key={i} className="border-t border-border last:border-b">
                <button
                  type="button"
                  id={triggerId}
                  aria-expanded={isOpen}
                  aria-controls={panelId}
                  onClick={() => setOpen(isOpen ? null : i)}
                  className="w-full py-4 flex items-start justify-between gap-6 text-left group"
                >
                  <span className="font-display text-lg md:text-xl font-medium text-foreground group-hover:text-brand transition-colors duration-base">
                    {item.q}
                  </span>
                  <span className="shrink-0 mt-1" aria-hidden="true">
                    {isOpen ? (
                      <Minus size={20} strokeWidth={1.75} className="text-accent-600 dark:text-accent-400" />
                    ) : (
                      <Plus size={20} strokeWidth={1.75} className="text-muted group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors" />
                    )}
                  </span>
                </button>
                <div
                  id={panelId}
                  role="region"
                  aria-labelledby={triggerId}
                  aria-hidden={!isOpen}
                  className={clsx(
                    "grid transition-all duration-slow ease-out-expo overflow-hidden",
                    isOpen ? "grid-rows-[1fr] pb-6" : "grid-rows-[0fr]",
                  )}
                >
                  <div className="overflow-hidden">
                    <p className="text-foreground/70 leading-relaxed text-base md:text-lg">
                      {item.a}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
