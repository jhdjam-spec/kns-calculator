"use client";

import { Heart, ArrowRight, ExternalLink } from "lucide-react";

/**
 * Карточка «Поддержать автора» — донат через YooMoney fundraise.
 *
 * Используется новый формат YooMoney «Fundraise» — целевой сбор средств с
 * прогресс-баром, статистикой, фото автора и видимой целью. Лучше чем
 * прежний /to/<wallet> потому что:
 *  - показывает прогресс цели (психологический мотиватор)
 *  - агрегирует все донаты в одну страницу
 *  - есть нативный виджет (iframe), который можно встроить на сайт
 *
 * billNumber `1HQ93GCV7OQ.260517` выдан YooMoney при создании сбора.
 */
const FUNDRAISE_ID = "1HQ93GCV7OQ.260517";
const FUNDRAISE_PAGE = `https://yoomoney.ru/fundraise/${FUNDRAISE_ID}`;
const FUNDRAISE_WIDGET = `https://yoomoney.ru/quickpay/fundraise/widget?billNumber=${FUNDRAISE_ID}&`;

export function DonateCard() {
  return (
    <section
      id="donate"
      className="py-20 md:py-24 bg-background dark:bg-ink-950 border-t border-border dark:border-white/[0.08]"
    >
      <div className="max-w-5xl mx-auto px-5 md:px-10">
        <div className="rounded-block bg-clover-50 dark:bg-clover-900/30 border border-clover-200 dark:border-clover-700/40 p-6 md:p-10">
          <div className="grid lg:grid-cols-[1fr,auto] gap-8 lg:gap-12 items-start">
            {/* Текст + крупная CTA-кнопка на полный лендинг */}
            <div>
              <div className="flex items-start gap-4 mb-6">
                <span className="shrink-0 inline-flex items-center justify-center h-12 w-12 rounded-full bg-clover-500 text-white">
                  <Heart size={22} strokeWidth={1.75} aria-hidden="true" />
                </span>
                <div>
                  <div className="text-xs font-mono uppercase tracking-wider text-clover-700 dark:text-clover-300 mb-1">
                    Поддержать проект
                  </div>
                  <h2 className="font-display text-2xl md:text-3xl font-semibold text-foreground dark:text-ink-50 leading-tight">
                    Калькулятор работает на энтузиазме
                  </h2>
                </div>
              </div>

              <p className="text-base md:text-lg text-foreground/80 dark:text-ink-200 leading-relaxed mb-2">
                Проект развивается на собственные средства автора и Серво-Юг.
                Поддержка идёт на хостинг, домен и ежемесячное обновление базы
                из 494 моделей насосов.
              </p>
              <p className="text-sm text-muted dark:text-ink-400 leading-relaxed mb-6">
                Бесплатно для пользователей · без рекламы · без сбора данных.
                Серверу нужно немного хлеба :)
              </p>

              <a
                href={FUNDRAISE_PAGE}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Поддержать на YooMoney — открыть страницу сбора"
                className="group inline-flex items-center justify-center gap-2 min-h-14 px-6 sm:px-8 rounded-md bg-clover-500 hover:bg-clover-600 hover:-translate-y-0.5 text-white font-medium transition-all duration-200 shadow-brand"
              >
                <Heart size={18} strokeWidth={1.75} aria-hidden="true" />
                <span>Поддержать на YooMoney</span>
                <ArrowRight
                  size={16}
                  strokeWidth={2}
                  className="transition-transform duration-base group-hover:translate-x-0.5"
                  aria-hidden="true"
                />
              </a>

              <p className="mt-5 text-xs font-mono text-muted dark:text-ink-500 flex items-center gap-1.5">
                <ExternalLink size={11} strokeWidth={1.75} aria-hidden="true" />
                Карты, СБП, Yandex Pay · без регистрации · спасибо :)
              </p>
            </div>

            {/* Виджет YooMoney Fundraise — встроенный с прогрессом сбора.
                500×480 — фиксированный размер от YooMoney, на mobile <lg
                переезжает вниз через grid. */}
            <div className="shrink-0 w-full lg:w-[500px]">
              <div className="rounded-md overflow-hidden bg-white dark:bg-white shadow-premium-sm border border-clover-200 dark:border-clover-700/40">
                <iframe
                  src={FUNDRAISE_WIDGET}
                  width="500"
                  height="480"
                  frameBorder="0"
                  allowTransparency
                  scrolling="no"
                  title="YooMoney — сбор средств на поддержку автора"
                  loading="lazy"
                  className="w-full block"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
