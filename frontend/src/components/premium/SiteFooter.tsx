import { Phone, Mail, MapPin } from "lucide-react";
import { InservoSignature } from "@/components/InservoSignature";

export function SiteFooter() {
  return (
    <footer className="bg-background dark:bg-ink-950 border-t border-border dark:border-white/[0.08] pt-16 pb-8">
      <div className="max-w-7xl mx-auto px-5 md:px-10">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-10 lg:gap-12 mb-12">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="size-8 rounded-md bg-accent-500 flex items-center justify-center">
                <span className="font-display font-bold text-ink-950 text-sm">И·С</span>
              </div>
              <div className="font-display font-semibold text-foreground dark:text-ink-50 text-sm tracking-wide uppercase">
                ИНСЕРВО · Серво-Юг
              </div>
            </div>
            <p className="text-sm text-muted dark:text-ink-400 leading-relaxed">
              Производство КНС, ЛОС, СПД и резервуаров с 2009 года. Подбор оборудования,
              шеф-монтаж и сервис.
            </p>
          </div>

          {/* Product */}
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-muted dark:text-ink-500 mb-4">
              Продукт
            </div>
            <ul className="space-y-2 text-sm text-foreground/80 dark:text-ink-300">
              <li>
                <a
                  href="#calculator"
                  className="hover:text-accent-500 transition-colors duration-fast"
                >
                  Калькулятор подбора
                </a>
              </li>
              <li>
                <a
                  href="/tanks"
                  className="hover:text-accent-500 transition-colors duration-fast"
                >
                  Калькуляторы ёмкостей
                </a>
              </li>
              <li>
                <a
                  href="#how"
                  className="hover:text-accent-500 transition-colors duration-fast"
                >
                  Как работает алгоритм
                </a>
              </li>
              <li>
                <a
                  href="#faq"
                  className="hover:text-accent-500 transition-colors duration-fast"
                >
                  FAQ
                </a>
              </li>
            </ul>
          </div>

          {/* Production */}
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-muted dark:text-ink-500 mb-4">
              Производство
            </div>
            <ul className="space-y-2 text-sm text-foreground/80 dark:text-ink-300">
              <li>
                <a
                  href="#trust"
                  className="hover:text-accent-500 transition-colors duration-fast"
                >
                  О компании
                </a>
              </li>
              <li>Сертификаты</li>
              <li>Объекты</li>
              <li>Договорная оферта</li>
            </ul>
          </div>

          {/* Contacts */}
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-muted dark:text-ink-500 mb-4">
              Контакты
            </div>
            <ul className="space-y-3 text-sm text-foreground/80 dark:text-ink-300">
              <li>
                <a
                  href="tel:+78002224457"
                  className="inline-flex items-center gap-2 hover:text-accent-500 transition-colors"
                >
                  <Phone size={14} strokeWidth={1.5} />
                  <span className="font-mono tabular-nums">8 (800) 222-44-57</span>
                </a>
              </li>
              <li>
                <a
                  href="mailto:zakaz@inservo.ru"
                  className="inline-flex items-center gap-2 hover:text-accent-500 transition-colors"
                >
                  <Mail size={14} strokeWidth={1.5} />
                  zakaz@inservo.ru
                </a>
              </li>
              <li className="inline-flex items-start gap-2 text-muted dark:text-ink-400">
                <MapPin size={14} strokeWidth={1.5} className="mt-0.5 shrink-0" />
                <span>Адыгея, аул Хатукай — производство и склад</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Authorship signature — INSERVO Studio (см. ADR-002) */}
        <div className="pt-8 border-t border-border dark:border-white/[0.06] mb-6">
          <InservoSignature />
        </div>

        {/* Bottom bar */}
        <div className="pt-6 border-t border-border dark:border-white/[0.06] flex flex-col md:flex-row md:items-center md:justify-between gap-3 text-xs font-mono text-muted dark:text-ink-500 tabular-nums">
          <div>© 2009–2026 · ИНСЕРВО · Серво-Юг</div>
          <div className="italic">Сделано в Краснодарском крае</div>
        </div>
      </div>
    </footer>
  );
}
