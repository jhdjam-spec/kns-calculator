import { Award, Building2, MapPin, Clock } from "lucide-react";

const kpis = [
  { value: "17", label: "лет на рынке", icon: Clock },
  { value: "284", label: "модели насосов в базе", icon: Building2 },
  { value: "1400+", label: "станций введено в эксплуатацию", icon: Award },
  { value: "7", label: "регионов поставки", icon: MapPin },
];

export function Trust() {
  return (
    <section id="trust" className="py-24 md:py-32 bg-background border-t border-border">
      <div className="max-w-7xl mx-auto px-5 md:px-10">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
          {/* Left: heading + KPIs */}
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-muted mb-4">
              <span className="block w-6 h-px bg-accent-500" />
              ПРОИЗВОДИТЕЛЬ
            </div>
            <h2 className="font-display text-4xl md:text-5xl lg:text-6xl font-semibold text-foreground leading-[1.05] tracking-tighter mb-6">
              Производим.
              <br />
              <span className="font-normal italic text-accent-600 dark:text-accent-400">Не перепродаём.</span>
            </h2>
            <p className="text-lg text-foreground/70 leading-relaxed mb-10 max-w-xl">
              Серво-Юг с 2009 года выпускает канализационные насосные станции,
              локальные очистные сооружения и резервуары. Своё производство в Адыгее,
              шеф-монтаж по Краснодарскому краю и югу России.
            </p>

            <div className="grid grid-cols-2 gap-px bg-border">
              {kpis.map(({ value, label, icon: Icon }) => (
                <div key={label} className="bg-surface p-6">
                  <div className="flex items-baseline gap-3 mb-2">
                    <span className="font-display text-4xl md:text-5xl font-semibold text-foreground tabular-nums leading-none">
                      {value}
                    </span>
                    <span className="block w-6 h-px bg-accent-500" />
                  </div>
                  <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-muted">
                    <Icon size={12} strokeWidth={1.5} />
                    {label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: production placeholder */}
          <div className="aspect-[4/5] rounded-block bg-border relative overflow-hidden">
            <div
              className="absolute inset-0"
              style={{
                background:
                  "linear-gradient(135deg, rgb(20 32 51) 0%, rgb(56 56 52) 50%, rgb(120 120 113) 100%)",
              }}
            />
            <div
              className="absolute inset-0 opacity-40"
              style={{
                backgroundImage: `repeating-linear-gradient(
                  -45deg,
                  transparent,
                  transparent 12px,
                  rgba(255,255,255,0.03) 12px,
                  rgba(255,255,255,0.03) 24px
                )`,
              }}
            />
            <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-ink-950 to-transparent p-6 md:p-8">
              <div className="text-[10px] font-mono uppercase tracking-widest text-accent-500 mb-1">
                ПРОИЗВОДСТВЕННЫЙ ЦЕХ
              </div>
              <div className="font-display text-xl md:text-2xl font-semibold text-ink-50">
                Адыгея, аул Хатукай
              </div>
              <div className="text-sm text-ink-300 mt-1">
                Сварка коллекторов, сборка щитов управления, гидроиспытания
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
