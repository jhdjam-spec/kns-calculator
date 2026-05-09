import { ClipboardList, Cpu, FileText } from "lucide-react";

const steps = [
  {
    n: "01",
    icon: ClipboardList,
    title: "Введите параметры",
    body: "Расход Q (м³/ч), напор H (м), тип объекта. Если не знаете расход — встроенный помощник посчитает по числу квартир, гостиничных номеров или площади кровли.",
  },
  {
    n: "02",
    icon: Cpu,
    title: "Алгоритм считает",
    body: "Гидравлика по СП 32.13330. Проверка попадания в рабочую зону насоса (AOR — Allowable Operating Range, POR — Preferred Operating Range по ANSI/HI). Фильтр по типу рабочего колеса (импеллера) и проходному сечению — чтобы насос не забивался волокнами или включениями. Сравнение 284 моделей за миллисекунды.",
  },
  {
    n: "03",
    icon: FileText,
    title: "Получите спецификацию",
    body: "Топ-3 насоса в трёх ценовых сегментах (бюджет / средний / премиум) с диапазоном цены комплекта (±10%). Опросный лист DOCX и черновик BOM (списка оборудования) — для тендера или КП за 1 рабочий день.",
  },
];

export function HowItWorks() {
  return (
    <section id="how" className="py-24 md:py-32 bg-ink-50 border-t border-ink-200">
      <div className="max-w-7xl mx-auto px-5 md:px-10">
        <div className="mb-16 md:mb-20 max-w-2xl">
          <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-ink-500 mb-4">
            <span className="block w-6 h-px bg-accent-500" />
            ПРОЦЕСС
          </div>
          <h2 className="font-display text-3xl md:text-5xl font-semibold text-ink-950 leading-tight tracking-tight">
            Четыре минуты от ТЗ
            <br />
            до спецификации
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-px bg-ink-200">
          {steps.map(({ n, icon: Icon, title, body }) => (
            <div key={n} className="bg-ink-50 p-8 md:p-10 group">
              <div className="flex items-baseline gap-4 mb-6">
                <span className="font-display text-5xl md:text-6xl font-light text-accent-500 tabular-nums leading-none">
                  {n}
                </span>
                <Icon
                  size={28}
                  strokeWidth={1.5}
                  className="text-ink-400 group-hover:text-brand-700 transition-colors duration-base"
                />
              </div>
              <h3 className="font-display text-xl font-semibold text-ink-950 mb-3">
                {title}
              </h3>
              <p className="text-ink-600 leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
