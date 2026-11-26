import { Phone, Mail, MapPin } from "lucide-react";
import { InservoSignature } from "@/components/InservoSignature";
import { BrandLogo } from "@/components/BrandLogo";

/**
 * Footer с контактами Серво-Юг + авторской подписью INSERVO Studio
 * (Морозов Константин, ADR-002).
 * Контакты: inservo.ru (zakaz@inservo.ru, 8-800-222-44-57, 8-988-237-32-87).
 */
export function SiteFooter() {
  return (
    <footer className="bg-background dark:bg-ink-950 border-t border-border dark:border-white/[0.08] pt-16 pb-8">
      <div className="max-w-7xl mx-auto px-5 md:px-10">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-10 lg:gap-12 mb-12">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <span className="shrink-0 text-clover-500 dark:text-clover-300">
                <BrandLogo size={36} ariaLabel="" />
              </span>
              <div className="font-display font-semibold text-foreground dark:text-ink-50 text-base tracking-tight">
                Серво-Юг
              </div>
            </div>
            <p className="text-sm text-muted dark:text-ink-400 leading-relaxed">
              Производство КНС, ЛОС, СПД и резервуаров с 2009 года. Подбор оборудования,
              шеф-монтаж и сервис по югу России.
            </p>
            <p className="mt-3 font-display italic text-sm text-clover-600 dark:text-clover-300">
              Чисто, надёжно, надолго.
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
                  href="/storm/minimal"
                  className="hover:text-accent-500 transition-colors duration-fast"
                >
                  Расчёт ливнёвки
                </a>
              </li>
              <li>
                <a
                  href="/teach"
                  className="hover:text-accent-500 transition-colors duration-fast"
                >
                  Энциклопедия инженера
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
              <li>
                <a
                  href="#donate"
                  className="hover:text-clover-600 dark:hover:text-clover-300 transition-colors duration-fast inline-flex items-center gap-1"
                >
                  <span aria-hidden="true">♥</span>
                  Поддержать автора
                </a>
              </li>
              <li>
                <a
                  href="/legal"
                  className="hover:text-accent-500 transition-colors duration-fast"
                >
                  Правовая информация
                </a>
              </li>
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
                <div className="ml-6 text-xs text-muted dark:text-ink-500">
                  бесплатный по России
                </div>
              </li>
              <li>
                <a
                  href="tel:+79882373287"
                  className="inline-flex items-center gap-2 hover:text-accent-500 transition-colors"
                >
                  <Phone size={14} strokeWidth={1.5} />
                  <span className="font-mono tabular-nums">8 (988) 237-32-87</span>
                </a>
                <div className="ml-6 text-xs text-muted dark:text-ink-500">
                  WhatsApp · Telegram · MAX
                </div>
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
                <span>
                  Краснодарский край · Адыгея
                  <br />
                  Производство и поставка по югу России
                </span>
              </li>
            </ul>
          </div>

          {/* Соцсети — tile-сетка по примеру inservo.ru. Тёмная плитка с brand-зелёным
              hover. Иконки текстовые, чтобы избежать лицензионных рисков с brand-glyphs. */}
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-muted dark:text-ink-500 mb-4">
              Социальные сети
            </div>
            <div className="grid grid-cols-3 gap-2 mb-2">
              {[
                { href: "https://rutube.ru/channel/inservo", label: "Rutube" },
                { href: "https://dzen.ru/inservo", label: "Дзен" },
                { href: "https://t.me/inservo", label: "Telegram" },
                { href: "https://youtube.com/@inservo", label: "YouTube" },
                { href: "https://max.ru/inservo", label: "MAX" },
                { href: "https://yandex.ru/ritm/inservo", label: "Ритм" },
              ].map((s) => (
                <a
                  key={s.href}
                  href={s.href}
                  target="_blank"
                  rel="noopener noreferrer nofollow"
                  aria-label={`Серво-Юг в ${s.label}`}
                  className="inline-flex items-center justify-center min-h-11 px-2 py-2 rounded-md text-xs font-medium text-foreground/80 dark:text-ink-200 bg-surface dark:bg-white/[0.04] border border-border dark:border-white/[0.06] hover:bg-clover-500/10 hover:text-clover-600 dark:hover:text-clover-300 hover:border-clover-500/40 transition-colors duration-base"
                >
                  {s.label}
                </a>
              ))}
            </div>
            <div className="mt-5 text-xs text-muted dark:text-ink-500 leading-relaxed">
              Партнёрские проекты:
              <ul className="mt-1.5 space-y-1">
                <li>
                  <a
                    href="https://inservo.ru"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-accent-500 transition-colors"
                  >
                    inservo.ru — септики
                  </a>
                </li>
                <li>
                  <a
                    href="https://emkosti.pro"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-accent-500 transition-colors"
                  >
                    emkosti.pro — ёмкости
                  </a>
                </li>
                <li>
                  <a
                    href="https://servotank.ru"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-accent-500 transition-colors"
                  >
                    servotank.ru — резервуары
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Disclaimer о точности расчётов */}
        <div className="pt-8 mt-2 border-t border-border dark:border-white/[0.06] text-xs font-mono text-muted dark:text-ink-500 leading-relaxed">
          Калькулятор даёт предварительный подбор. Перед заказом параметры проверяет инженер.
          Не является публичной офертой.
        </div>

        {/* Authorship signature — Layout Stars Studio · Константин Морозов (ADR-002).
            Содержит copyright + лицензию. Гео-метку «Сделано в Краснодарском крае»
            убрали — пафосно для B2B-инструмента по итогам copy-аудита. */}
        <div className="pt-8 mt-6 border-t border-border dark:border-white/[0.06] mb-4">
          <InservoSignature />
        </div>
      </div>
    </footer>
  );
}
