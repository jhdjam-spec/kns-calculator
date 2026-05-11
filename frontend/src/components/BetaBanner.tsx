// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { AlertTriangle } from "lucide-react";

/**
 * Глобальный баннер «бета-версия» — статичная жёлтая полоса в верхней части
 * страницы (НЕ sticky, чтобы не перекрывать SiteNav на мобильных). Не закрывается,
 * не сворачивается. Высота ~32px на mobile / ~36px на desktop; SiteNav остаётся
 * sticky top-0 ниже баннера.
 *
 * Цель: защитить менеджеров/сметчиков от переноса результата калькулятора в
 * ТЗ без проверки инженером. Калькулятор даёт оценочный расчёт; финальные
 * параметры подтверждает инженер ПТО.
 */
export function BetaBanner() {
  return (
    <div
      role="status"
      aria-label="Статус калькулятора: бета-версия"
      className="relative z-30 bg-amber-400 text-ink-950 border-b border-amber-500"
    >
      <div className="max-w-7xl mx-auto px-5 md:px-10 py-1.5 md:py-2 flex items-start md:items-center gap-3 text-xs md:text-sm">
        <AlertTriangle
          size={16}
          strokeWidth={2.2}
          className="shrink-0 mt-0.5 md:mt-0"
          aria-hidden="true"
        />
        <p className="leading-snug">
          <strong className="font-semibold">Бета.</strong>
          <span className="md:hidden"> Точность ±15% — финальный расчёт у инженера.</span>
          <span className="hidden md:inline">
            {" "}Инструмент в активной разработке. Точность ±15% от паспортного расчёта —
            подходит для тендера, ТЭО и КП. Для финального проекта согласуйте с инженером
            Серво-Юг.
          </span>
        </p>
      </div>
    </div>
  );
}
