// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { AlertTriangle } from "lucide-react";

/**
 * Глобальный баннер «бета-версия» — фиксированная жёлтая полоса в верхней части
 * страницы. Не закрывается, не сворачивается.
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
      className="sticky top-0 z-50 bg-amber-400 text-ink-950 border-b border-amber-500"
    >
      <div className="max-w-7xl mx-auto px-5 md:px-10 py-2 flex items-start md:items-center gap-3 text-xs md:text-sm">
        <AlertTriangle
          size={16}
          strokeWidth={2.2}
          className="shrink-0 mt-0.5 md:mt-0"
          aria-hidden="true"
        />
        <p className="leading-snug">
          <strong className="font-semibold">Бета-версия.</strong>
          <span className="md:hidden"> Расчёт проверяет инженер.</span>
          <span className="hidden md:inline">
            {" "}Результаты информативные. Перед коммерческим использованием расчёт обязательно
            проверяет инженер.
          </span>
        </p>
      </div>
    </div>
  );
}
