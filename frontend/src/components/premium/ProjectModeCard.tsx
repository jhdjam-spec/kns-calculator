"use client";

import { ArrowRight } from "lucide-react";

/**
 * Секция «Какой режим вам нужен» — две карточки:
 * 1. Проект целиком (визард) — для ГИП и проектировщика
 * 2. Быстрый подбор (Hero+Calculator) — для менеджера КП
 *
 * Размещается на главной между HowItWorks и CalculatorPanel.
 */
export function ProjectModeCard() {
  return (
    <section
      id="modes"
      className="relative py-16 md:py-24 px-5 md:px-10 bg-ink-50"
    >
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-10">
          <div className="text-xs font-mono uppercase tracking-wider text-ink-500 mb-3">
            Два режима работы
          </div>
          <h2 className="text-3xl md:text-4xl font-display font-bold text-ink-950 mb-4">
            Подбор насоса или проект целиком?
          </h2>
          <p className="text-ink-600 max-w-2xl mx-auto">
            Калькулятор работает в двух режимах. Выберите тот, что подходит вашей задаче.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Project mode */}
          <a
            href="/project"
            className="group block p-7 md:p-8 bg-ink-950 rounded-xl border border-accent-500/30 hover:border-accent-500 transition-all hover:shadow-2xl hover:-translate-y-0.5"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="text-xs font-mono uppercase tracking-wider text-accent-500">
                Полный расчёт проекта
              </div>
              <div className="px-2 py-0.5 bg-accent-500 text-ink-950 text-xs font-mono rounded">
                Рекомендуем
              </div>
            </div>
            <div className="text-2xl md:text-3xl font-display font-bold text-ink-50 mb-3">
              Проект целиком
            </div>
            <div className="text-ink-300 mb-6 leading-relaxed">
              Выбираете тип объекта (ИЖС, ЖК, АЗС, гостиница и т.п.), вводите базовые параметры —
              калькулятор прогонит расчёты по всем инженерным системам: <strong>КНС</strong>{" "}
              (канализация), <strong>ВНС</strong> (водоснабжение), пожаротушение, очистные (ЛОС),
              электрика, климат и прочность корпуса.
            </div>
            <div className="flex flex-wrap gap-1.5 mb-6">
              {[
                "Все расчёты сразу",
                "Ссылки на СП и ГОСТ",
                "Готов к защите проекта",
                "Для ГИП и инженера-проектировщика",
              ].map((tag) => (
                <span
                  key={tag}
                  className="text-xs px-2.5 py-1 bg-ink-800 text-ink-300 rounded font-mono"
                >
                  {tag}
                </span>
              ))}
            </div>
            <div className="flex items-center gap-2 text-accent-500 font-medium">
              Запустить визард проекта
              <ArrowRight
                size={16}
                strokeWidth={2}
                className="transition-transform group-hover:translate-x-1"
              />
            </div>
          </a>

          {/* Quick mode */}
          <a
            href="#calculator"
            className="group block p-7 md:p-8 bg-ink-100 rounded-xl border border-ink-200 hover:border-ink-400 transition-all hover:shadow-xl hover:-translate-y-0.5"
          >
            <div className="text-xs font-mono uppercase tracking-wider text-ink-500 mb-4">
              Быстрый подбор насоса
            </div>
            <div className="text-2xl md:text-3xl font-display font-bold text-ink-950 mb-3">
              Только насос
            </div>
            <div className="text-ink-700 mb-6 leading-relaxed">
              4 поля: расход <strong>Q</strong> м³/ч, перепад высот <strong>dH</strong> м,
              длина напорной линии <strong>L</strong> м, тип стоков. Получаете топ-3 моделей в
              трёх ценовых сегментах с предварительной стоимостью комплекта. Для оперативного
              КП или ранней оценки бюджета.
            </div>
            <div className="flex flex-wrap gap-1.5 mb-6">
              {[
                "Подбор за 30 сек",
                "Бюджет / средний / премиум",
                "Только насос",
                "Для менеджера и ГИП",
              ].map((tag) => (
                <span
                  key={tag}
                  className="text-xs px-2.5 py-1 bg-ink-200 text-ink-600 rounded font-mono"
                >
                  {tag}
                </span>
              ))}
            </div>
            <div className="flex items-center gap-2 text-ink-700 font-medium">
              Перейти к подбору
              <ArrowRight
                size={16}
                strokeWidth={2}
                className="transition-transform group-hover:translate-x-1"
              />
            </div>
          </a>
        </div>

        <div className="mt-8 text-center">
          <a
            href="/teach"
            className="inline-flex items-center gap-2 text-sm text-ink-600 hover:text-ink-950 font-medium transition-colors"
          >
            📚 Или откройте Энциклопедию инженера ВК
            <ArrowRight size={14} />
          </a>
        </div>
      </div>
    </section>
  );
}
