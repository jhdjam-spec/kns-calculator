"use client";

import { type CaseKind } from "./CaseIllustration";
import { CasePhoto } from "./CasePhoto";

interface Case {
  type: string;
  kind: CaseKind;
  location: string;
  rooms: string;
  Q: string;
  H: string;
  model: string;
}

const cases: Case[] = [
  {
    type: "Гостиница 4★",
    kind: "hotel",
    location: "Анапа · 2025",
    rooms: "120 номеров",
    Q: "26 м³/ч",
    H: "14 м",
    model: "Pedrollo MCm 40 ×2",
  },
  {
    type: "ЖК",
    kind: "residential",
    location: "Краснодар · 2024",
    rooms: "320 квартир",
    Q: "45 м³/ч",
    H: "18 м",
    model: "Antarus AK2 80 ×2+1",
  },
  {
    type: "ТРЦ",
    kind: "mall",
    location: "Ростов-на-Дону · 2024",
    rooms: "30 000 м²",
    Q: "120 м³/ч",
    H: "28 м",
    model: "KAIQUAN WQ200-12 ×3",
  },
  {
    type: "Дренаж кровли",
    kind: "roof_drain",
    location: "Сочи · 2025",
    rooms: "5 га асфальта",
    Q: "974 м³/ч",
    H: "23.6 м",
    model: "ONIS SW250 ×3",
  },
];

export function Cases() {
  return (
    <section className="py-24 md:py-32 bg-background dark:bg-ink-950 relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-30 hidden dark:block"
        style={{
          background:
            "radial-gradient(ellipse 1000px 500px at 80% 50%, rgba(30, 58, 95, 0.5), transparent 70%)",
        }}
      />

      <div className="relative max-w-7xl mx-auto px-5 md:px-10">
        <div className="mb-12 md:mb-16 max-w-2xl">
          <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-muted dark:text-ink-300 mb-4">
            <span className="block w-6 h-px bg-accent-500" />
            ОБЪЕКТЫ
          </div>
          <h2 className="font-display text-3xl md:text-5xl font-semibold text-foreground dark:text-ink-50 leading-tight tracking-tight">
            Реальные расчёты —
            <br />
            подобраны и поставлены
          </h2>
        </div>

        <div
          role="region"
          aria-label="Кейсы — горизонтальная карусель, прокручивается стрелками клавиатуры"
          tabIndex={0}
          className="scroll-rail flex gap-4 md:gap-6 overflow-x-auto -mx-5 md:-mx-10 px-5 md:px-10 pb-4 snap-x snap-mandatory focus:outline-none focus-visible:ring-2 focus-visible:ring-clover-500"
        >
          {cases.map((c) => (
            <div
              key={`${c.type}-${c.location}`}
              className="snap-start shrink-0 w-[300px] md:w-[360px] rounded-card bg-surface dark:bg-white/[0.03] border border-border dark:border-white/[0.08] overflow-hidden hover:border-accent-500/30 transition-colors duration-base"
            >
              {/* Stock-фото + SVG-wireframe overlay + clover-gradient */}
              <div className="aspect-[4/3] bg-gradient-to-br from-ink-900 to-ink-800 relative overflow-hidden">
                <CasePhoto kind={c.kind} alt={`${c.type} — ${c.location}, ${c.rooms}`} />
                <div className="absolute top-3 left-3 inline-flex items-center gap-1.5 px-2 py-1 rounded bg-clover-700/80 backdrop-blur-sm text-[10px] font-mono uppercase tracking-wider text-clover-50 z-10 shadow-lg">
                  <span className="block w-1.5 h-1.5 rounded-full bg-clover-300 shadow-[0_0_6px_rgba(154,224,184,0.9)]" />
                  {c.type}
                </div>
              </div>

              {/* Body */}
              <div className="p-6">
                <div className="text-xs font-mono text-muted dark:text-ink-400 mb-3">{c.location}</div>
                <div className="font-display text-lg font-semibold text-foreground dark:text-ink-50 mb-1">
                  {c.rooms}
                </div>
                <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-border dark:border-white/[0.06]">
                  <div>
                    <div className="text-[9px] font-mono uppercase tracking-wider text-muted dark:text-ink-500">
                      Q
                    </div>
                    <div className="font-mono tabular-nums text-foreground dark:text-ink-50 text-sm">{c.Q}</div>
                  </div>
                  <div>
                    <div className="text-[9px] font-mono uppercase tracking-wider text-muted dark:text-ink-500">
                      H
                    </div>
                    <div className="font-mono tabular-nums text-foreground dark:text-ink-50 text-sm">{c.H}</div>
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t border-border dark:border-white/[0.06]">
                  <div className="text-[9px] font-mono uppercase tracking-wider text-muted dark:text-ink-500 mb-1">
                    Установлено
                  </div>
                  <div className="text-foreground dark:text-ink-200 text-sm">{c.model}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
