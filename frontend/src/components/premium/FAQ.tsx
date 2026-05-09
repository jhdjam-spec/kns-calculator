"use client";

import { useState } from "react";
import { Plus, Minus } from "lucide-react";
import clsx from "clsx";

const faqs = [
  {
    q: "Чем подбор по калькулятору отличается от расчёта проектного института?",
    a: "Калькулятор делает первичный подбор по гидравлическим параметрам Q (расход) и H (напор) — для тендера, ТЭО (технико-экономического обоснования) или КП. Это инженерный ориентир за минуты, не замена проекту. Для сложных объектов (I категория надёжности, длинные трассы, агрессивные среды) расчёт уточняет инженер Серво-Юг — и результат соответствует требованиям СП 32.13330 (канализация наружная) и СП 10.13130 (внутренний пожарный водопровод).",
  },
  {
    q: "Можно ли получить КМД-чертёж (рабочую документацию) после подбора?",
    a: "Да. КМД — конструкции металлические деталировочные (рабочие чертежи на изготовление). После передачи данных инженеру (через DOCX-опросник или звонок) высылаем спецификацию с печатью, схему обвязки и КМД на станцию в формате PDF / DWG за 1 рабочий день.",
  },
  {
    q: "Какие гарантии на оборудование и какой срок поставки?",
    a: "На станции собственного производства — 24 месяца, на насосы — 12 месяцев согласно гарантии производителя. Срок поставки стандартных решений — от 7 рабочих дней при предоплате, нестандартных (большие диаметры, корпуса >D2400 мм) — от 30 дней.",
  },
  {
    q: "Подходит ли подбор для объектов с переменным расходом (гостиницы, ЖК)?",
    a: "Да. Калькулятор учитывает СП 30.13330 прил. А.2: коэффициент часовой неравномерности 2.5–4.5 встроен в QHelper по типу объекта. Для нестандартного режима (производство со сменами) — выберите помощник «Расход на смену» или передайте данные инженеру.",
  },
  {
    q: "Делаете ли вы шеф-монтаж и пусконаладку (ПНР) в Краснодарском крае?",
    a: "Да. Шеф-монтаж и ПНР (пусконаладочные работы) — собственными бригадами по Краснодарскому краю, Адыгее, Ростовской области, Крыму и Ставрополью. На дальние регионы — выезд по согласованию (стоимость рассчитывается отдельно).",
  },
  {
    q: "Как учитывается заглубление и грунтовые воды?",
    a: "Глубина заложения и УГВ (уровень грунтовых вод) — параметры расширенного расчёта. Если вода стоит выше дна КНС — корпус усиливается противоразмывными рёбрами, для глубин >6 м применяется стеклопластиковый корпус. Калькулятор предложит подходящий материал; финальная проверка — у инженера по геологическим данным с участка.",
  },
];

export function FAQ() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section id="faq" className="py-24 md:py-32 bg-ink-50 border-t border-ink-200">
      <div className="max-w-3xl mx-auto px-5 md:px-10">
        <div className="mb-12 md:mb-16">
          <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-ink-500 mb-4">
            <span className="block w-6 h-px bg-accent-500" />
            FAQ
          </div>
          <h2 className="font-display text-3xl md:text-4xl lg:text-5xl font-semibold text-ink-950 leading-tight tracking-tight">
            Частые вопросы
          </h2>
        </div>

        <div>
          {faqs.map((item, i) => (
            <div key={i} className="border-t border-ink-200 last:border-b">
              <button
                type="button"
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full py-6 md:py-7 flex items-start justify-between gap-6 text-left group"
              >
                <span className="font-display text-lg md:text-xl font-medium text-ink-950 group-hover:text-brand-700 transition-colors duration-base">
                  {item.q}
                </span>
                <span className="shrink-0 mt-1">
                  {open === i ? (
                    <Minus size={20} strokeWidth={1.75} className="text-accent-600" />
                  ) : (
                    <Plus size={20} strokeWidth={1.75} className="text-ink-400 group-hover:text-accent-600 transition-colors" />
                  )}
                </span>
              </button>
              <div
                className={clsx(
                  "grid transition-all duration-slow ease-out-expo overflow-hidden",
                  open === i ? "grid-rows-[1fr] pb-6" : "grid-rows-[0fr]",
                )}
              >
                <div className="overflow-hidden">
                  <p className="text-ink-600 leading-relaxed text-base md:text-lg">
                    {item.a}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
