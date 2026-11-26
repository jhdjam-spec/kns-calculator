import type { Metadata } from "next";
import { SiteNav } from "@/components/premium/SiteNav";
import { SiteFooter } from "@/components/premium/SiteFooter";

export const metadata: Metadata = {
  title: "Правовая информация · Серво-Юг",
  description:
    "Правовые сведения, реквизиты, политика конфиденциальности и условия использования калькулятора подбора КНС / ЛОС / СПД.",
  alternates: { canonical: "/legal" },
  robots: { index: true, follow: true },
};

/**
 * Страница правовой информации. Обязательна при:
 *  - сборе пожертвований через YooMoney от физлица-получателя (152-ФЗ)
 *  - размещении рекламы на сайте (38-ФЗ ст.8 — обязательное указание ОГРНИП/ИНН)
 *  - сборе любых персональных данных через формы (152-ФЗ — политика конф.)
 *
 * Реквизиты указаны как **источник проекта**, не как продавец услуг.
 * Серво-Юг — отдельное юр.лицо (производственная компания), его реквизиты
 * не дублируем без явного согласия.
 */
export default function LegalPage() {
  return (
    <>
      <SiteNav />
      <main id="main" className="kns-document min-h-screen bg-background dark:bg-ink-950 py-16 md:py-24">
        <article className="max-w-3xl mx-auto px-5 md:px-10">
          <header className="mb-10">
            <div className="text-xs font-mono uppercase tracking-wider text-clover-700 dark:text-clover-300 mb-3">
              Правовая информация
            </div>
            <h1 className="font-display text-3xl md:text-5xl font-semibold text-foreground dark:text-ink-50 leading-tight tracking-tight">
              Правовые сведения
            </h1>
            <p className="mt-4 text-base text-muted dark:text-ink-400">
              Калькулятор подбора КНС / ЛОС / СПД — некоммерческий инструмент.
              Информация на этой странице обязательна для соблюдения 38-ФЗ
              «О рекламе» и 152-ФЗ «О персональных данных».
            </p>
          </header>

          <section className="space-y-6">
            <div className="rounded-lg border border-border dark:border-white/10 bg-surface dark:bg-white/[0.02] p-6">
              <h2 className="font-display text-xl font-semibold text-foreground dark:text-ink-100 mb-3">
                Автор и правообладатель проекта
              </h2>
              <dl className="text-sm grid sm:grid-cols-[160px_1fr] gap-x-4 gap-y-2">
                <dt className="text-muted dark:text-ink-400">Автор</dt>
                <dd className="text-foreground dark:text-ink-100">
                  Морозов Константин · Layout Stars Studio by inservo.ru
                </dd>
                <dt className="text-muted dark:text-ink-400">Сайт студии</dt>
                <dd>
                  <a
                    href="https://inservo.ru"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-clover-700 dark:text-clover-300 underline underline-offset-2 decoration-clover-700/40 hover:decoration-clover-700"
                  >
                    https://inservo.ru
                  </a>
                </dd>
                <dt className="text-muted dark:text-ink-400">Лицензия кода</dt>
                <dd>MIT — открытый исходный код</dd>
                <dt className="text-muted dark:text-ink-400">Репозиторий</dt>
                <dd className="text-foreground/80 dark:text-ink-300">
                  Код проекта — opensource. Просьба сохранять подпись авторства.
                </dd>
              </dl>
            </div>

            <div className="rounded-lg border border-border dark:border-white/10 bg-surface dark:bg-white/[0.02] p-6">
              <h2 className="font-display text-xl font-semibold text-foreground dark:text-ink-100 mb-3">
                Партнёр проекта — Серво-Юг
              </h2>
              <p className="text-sm text-foreground/80 dark:text-ink-300 leading-relaxed mb-3">
                Калькулятор использует базу насосного оборудования и инженерные
                методики, предоставленные компанией <strong>Серво-Юг</strong> —
                российским производителем КНС, ЛОС и СПД-станций с 2009 года.
              </p>
              <dl className="text-sm grid sm:grid-cols-[160px_1fr] gap-x-4 gap-y-2">
                <dt className="text-muted dark:text-ink-400">Сайт</dt>
                <dd>
                  <a
                    href="https://inservo.ru"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-clover-700 dark:text-clover-300 underline underline-offset-2 decoration-clover-700/40 hover:decoration-clover-700"
                  >
                    inservo.ru
                  </a>{" "}
                  · {" "}
                  <a
                    href="https://emkosti.pro"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-clover-700 dark:text-clover-300 underline underline-offset-2 decoration-clover-700/40 hover:decoration-clover-700"
                  >
                    emkosti.pro
                  </a>{" "}
                  · {" "}
                  <a
                    href="https://servotank.ru"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-clover-700 dark:text-clover-300 underline underline-offset-2 decoration-clover-700/40 hover:decoration-clover-700"
                  >
                    servotank.ru
                  </a>
                </dd>
                <dt className="text-muted dark:text-ink-400">Телефон</dt>
                <dd className="font-mono tabular-nums">
                  <a href="tel:+78002224457" className="underline underline-offset-2 decoration-clover-700/40 hover:decoration-clover-700">8 (800) 222-44-57</a>
                  {" · "}
                  <a href="tel:+79882373287" className="underline underline-offset-2 decoration-clover-700/40 hover:decoration-clover-700">8 (988) 237-32-87</a>
                </dd>
                <dt className="text-muted dark:text-ink-400">Email</dt>
                <dd>
                  <a
                    href="mailto:zakaz@inservo.ru"
                    className="text-clover-700 dark:text-clover-300 underline underline-offset-2 decoration-clover-700/40 hover:decoration-clover-700"
                  >
                    zakaz@inservo.ru
                  </a>
                </dd>
                <dt className="text-muted dark:text-ink-400">Регион</dt>
                <dd>Краснодарский край (Сочи) · Республика Адыгея</dd>
              </dl>
              <p className="mt-3 text-xs text-muted dark:text-ink-500">
                За точными юридическими реквизитами (ОГРНИП, ИНН, расчётный счёт)
                для договоров обращайтесь напрямую к компании Серво-Юг через
                указанные контакты.
              </p>
            </div>

            <div className="rounded-lg border border-border dark:border-white/10 bg-surface dark:bg-white/[0.02] p-6">
              <h2 className="font-display text-xl font-semibold text-foreground dark:text-ink-100 mb-3">
                Пожертвования
              </h2>
              <p className="text-sm text-foreground/80 dark:text-ink-300 leading-relaxed mb-3">
                Кнопка «Поддержать автора» ведёт на сервис{" "}
                <a
                  href="https://yoomoney.ru/fundraise/1HQ93GCV7OQ.260517"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-clover-700 dark:text-clover-300 underline underline-offset-2 decoration-clover-700/40 hover:decoration-clover-700"
                >
                  YooMoney Fundraise
                </a>
                . Получатель пожертвований —{" "}
                <strong>физическое лицо Морозов Константин</strong>, автор
                калькулятора. Пожертвования{" "}
                <strong>не являются оплатой услуг</strong> и используются на
                поддержку инфраструктуры проекта (хостинг, домен, обновление
                базы насосов).
              </p>
              <p className="text-sm text-foreground/80 dark:text-ink-300 leading-relaxed">
                Согласно ст. 217 НК РФ п. 11.2, такие пожертвования не облагаются
                налогом у получателя в пределах установленного лимита. Оплата
                проходит через YooMoney с соблюдением 161-ФЗ и 115-ФЗ.
              </p>
            </div>

            <div className="rounded-lg border border-border dark:border-white/10 bg-surface dark:bg-white/[0.02] p-6">
              <h2 className="font-display text-xl font-semibold text-foreground dark:text-ink-100 mb-3">
                Персональные данные и cookies
              </h2>
              <ul className="text-sm text-foreground/80 dark:text-ink-300 leading-relaxed space-y-2 list-disc list-inside">
                <li>
                  Калькулятор работает{" "}
                  <strong>без регистрации и сбора персональных данных</strong>.
                </li>
                <li>
                  Введённые в форму параметры (расход, напор, тип объекта) не
                  сохраняются на сервере. Передаются только для расчёта и
                  возвращаются в виде результата.
                </li>
                <li>
                  Файлы DOCX/PDF, которые вы можете скачать, формируются на
                  лету — без сохранения данных.
                </li>
                <li>
                  Для технической работы используются собственные cookies
                  (предпочтения темы, режима). Аналитика отсутствует.
                </li>
                <li>
                  Если вы оставляете контакты через форму обратной связи —
                  они передаются напрямую Серво-Юг (zakaz@inservo.ru) и
                  используются только для ответа на ваш запрос (152-ФЗ).
                </li>
              </ul>
            </div>

            <div className="rounded-lg border border-border dark:border-white/10 bg-surface dark:bg-white/[0.02] p-6">
              <h2 className="font-display text-xl font-semibold text-foreground dark:text-ink-100 mb-3">
                Точность расчётов и ограничения
              </h2>
              <p className="text-sm text-foreground/80 dark:text-ink-300 leading-relaxed">
                Калькулятор предоставляет <strong>оценочные расчёты</strong>{" "}
                и предназначен для
                первичного подбора оборудования, подготовки ТЗ и КП.{" "}
                <strong>
                  Не является публичной офертой и не заменяет проектную
                  документацию.
                </strong>{" "}
                Финальные параметры подтверждает инженер ПТО проектной
                организации с учётом конкретной геологии участка, ТЗ заказчика
                и действующих нормативов СП 32.13330, СП 31.13330, СП 30.13330,
                СП 22.13330, ПУЭ.
              </p>
            </div>

            <div className="rounded-lg border border-border dark:border-white/10 bg-surface dark:bg-white/[0.02] p-6">
              <h2 className="font-display text-xl font-semibold text-foreground dark:text-ink-100 mb-3">
                Контакт по правовым вопросам
              </h2>
              <p className="text-sm text-foreground/80 dark:text-ink-300 leading-relaxed">
                По вопросам авторских прав, правового использования материалов
                и удалению данных пишите на{" "}
                <a
                  href="mailto:zakaz@inservo.ru"
                  className="text-clover-700 dark:text-clover-300 underline underline-offset-2 decoration-clover-700/40 hover:decoration-clover-700"
                >
                  zakaz@inservo.ru
                </a>{" "}
                — ответ в течение 1 рабочего дня.
              </p>
            </div>
          </section>

          <p className="mt-10 text-xs font-mono text-muted dark:text-ink-500 text-center">
            Последнее обновление: 2026-05-17
          </p>
        </article>
      </main>
      <SiteFooter />
    </>
  );
}
