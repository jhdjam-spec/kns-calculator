"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight, Phone, Menu, X, Heart, Search } from "lucide-react";
import clsx from "clsx";
import { ThemeToggle } from "@/components/ThemeToggle";
import { BrandLogo } from "@/components/BrandLogo";
import { useCommandPalette } from "@/components/providers/CommandPaletteProvider";

const NAV_LINKS: Array<{ href: string; label: string; primary?: boolean }> = [
  { href: "/project", label: "Проект целиком", primary: true },
  { href: "/storm/minimal", label: "Ливнёвка" },
  { href: "/tanks", label: "Резервуары" },
  { href: "/teach", label: "Энциклопедия" },
  { href: "/import", label: "Импорт ТЗ" },
  { href: "/#calculator", label: "Подбор насоса" },
  { href: "/#faq", label: "Вопросы" },
];

export function SiteNav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement | null>(null);
  const burgerRef = useRef<HTMLButtonElement | null>(null);
  const { setOpen: setPaletteOpen } = useCommandPalette();

  useEffect(() => {
    // Гистерезис чтобы не мигало на границе: scroll вниз > 120 → compact,
    // scroll вверх < 40 → expanded. Между 40 и 120 — состояние сохраняется.
    // Также throttle через requestAnimationFrame чтобы не дёргать setState на каждый tick.
    let rafId = 0;
    let lastY = window.scrollY;
    const onScroll = () => {
      if (rafId) return;
      rafId = requestAnimationFrame(() => {
        const y = window.scrollY;
        if (y > 120 && !lastY) setScrolled(true);
        if (y < 40 && lastY) setScrolled(false);
        // Используем функциональный update чтобы не зависеть от stale state
        setScrolled((prev) => {
          if (prev && y < 40) return false;
          if (!prev && y > 120) return true;
          return prev;
        });
        lastY = y;
        rafId = 0;
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, []);

  // Close on Esc + focus-trap внутри drawer + возврат фокуса на burger при закрытии
  useEffect(() => {
    if (!mobileOpen) return;

    const drawer = drawerRef.current;
    const getFocusable = (): HTMLElement[] => {
      if (!drawer) return [];
      return Array.from(
        drawer.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((el) => !el.hasAttribute("aria-hidden"));
    };

    // Перенесём фокус на первый интерактивный элемент drawer
    const firstFocusable = getFocusable()[0];
    firstFocusable?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMobileOpen(false);
        return;
      }
      if (e.key !== "Tab") return;
      const focusable = getFocusable();
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };

    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Сохраняем ссылку на burger в локальной переменной — на момент cleanup
    // burgerRef.current может уже измениться (React предупреждает).
    const burgerAtEffectTime = burgerRef.current;

    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
      burgerAtEffectTime?.focus();
    };
  }, [mobileOpen]);

  const closeMobile = () => setMobileOpen(false);

  return (
    <>
    <header
      className={clsx(
        // sticky top-0: висит под BetaBanner (BetaBanner static, не перекрывает на mobile).
        // Тема: в light режиме — светлый фон с лёгким blur, в dark — чёрный ink-950.
        // Раньше был жёсткий bg-ink-950 → на белой странице получалась чёрная полоса
        // в которой ссылки text-ink-300 хорошо видны, но контрастно ломали стиль.
        // ВАЖНО: backdrop-blur тут создаёт containing block для fixed-children
        // (баг WebKit/Blink), поэтому drawer вынесен НИЖЕ header в JSX,
        // иначе он схлопывается до высоты header.
        "kns-site-nav sticky top-0 z-40 transition-all duration-base ease-out-quart",
        scrolled
          ? "bg-white/85 dark:bg-ink-950/85 backdrop-blur-md backdrop-saturate-150 border-b border-ink-200/60 dark:border-white/[0.06]"
          : "bg-white/70 dark:bg-ink-950/40 backdrop-blur-sm",
      )}
    >
      {/* Строка 1: лого + меню + контакты */}
      <div
        className={clsx(
          "max-w-7xl mx-auto px-5 md:px-10 flex items-center justify-between gap-3 transition-all duration-base",
          scrolled ? "h-14" : "h-16 md:h-[72px]",
        )}
      >
        <a href="/" className="flex items-center gap-2.5 group min-h-11 shrink-0" aria-label="На главную, Серво-Юг">
          {/* Настоящий логотип Серво-Юг — четырёхлистный клевер. Цвет clover-500
              (#1F7A4D) — родной brand-color из brand-guide заказчика. */}
          <span className="shrink-0 text-clover-500 dark:text-clover-300">
            <BrandLogo size={32} ariaLabel="" />
          </span>
          {/* В одну строку чтобы не «прыгало» по высоте. «· калькулятор КНС»
              виден только на 2xl+ (>=1536px) когда есть запас по горизонтали. */}
          <span className="font-display font-semibold text-ink-900 dark:text-ink-50 text-base tracking-tight whitespace-nowrap">
            Серво-Юг
            <span className="ml-1.5 text-ink-500 dark:text-ink-400 text-xs font-mono hidden 2xl:inline">
              · калькулятор КНС
            </span>
          </span>
        </a>

        {/* Десктоп-нав. Только 3 ключевые ссылки видны в navbar (Проект, Энциклопедия, FAQ).
            Все 7 ссылок — через burger-меню (видим всегда, не только на mobile).
            Это решение исключает overlap на любых ширинах и не зависит от breakpoint. */}
        <nav className="hidden md:flex items-center gap-5 lg:gap-6 text-sm text-ink-700 dark:text-ink-300 min-w-0">
          {NAV_LINKS.filter((l) =>
            ["/project", "/teach", "#faq"].includes(l.href),
          ).map((link) => (
            <a
              key={link.href}
              href={link.href}
              className={clsx(
                "transition-colors duration-fast whitespace-nowrap",
                link.primary
                  ? "hover:text-clover-700 dark:hover:text-accent-500 font-medium"
                  : "hover:text-ink-900 dark:hover:text-ink-50",
              )}
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-1.5 md:gap-2 shrink-0">
          {/* Cmd+K триггер — Linear/Vercel-style command palette.
              Mobile (<sm): только иконка 44×44. Tablet (sm-md): иконка + Search.
              Desktop (md+): полный с ⌘K shortcut hint. */}
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            aria-label="Открыть командную палитру (Cmd+K)"
            title="Поиск и команды (⌘K)"
            className="inline-flex items-center justify-center sm:justify-start gap-2 min-h-11 min-w-11 h-11 px-2 sm:px-3 rounded-md border border-ink-300 dark:border-white/10 text-ink-700 dark:text-ink-300 text-xs font-mono hover:text-ink-900 dark:hover:text-ink-50 hover:border-ink-400 dark:hover:border-white/20 hover:bg-ink-100/50 dark:hover:bg-white/5 transition-colors"
          >
            <Search size={16} strokeWidth={1.75} />
            <span className="hidden sm:inline">Поиск</span>
            <kbd className="hidden md:inline-block text-[10px] uppercase tracking-wider text-ink-500 dark:text-ink-400 border border-ink-300 dark:border-white/10 rounded px-1 py-0.5">
              ⌘K
            </kbd>
          </button>
          {/* Phone — всегда только иконка-кнопка 44×44 без текста.
              Полный номер виден в footer и mobile drawer. */}
          <a
            href="tel:+78002224457"
            aria-label="Позвонить 8 800 222 44 57"
            title="8 (800) 222-44-57"
            className="inline-flex items-center justify-center min-h-11 min-w-11 h-11 px-2 rounded-md text-ink-700 dark:text-ink-50 hover:text-clover-700 dark:hover:text-accent-500 hover:bg-ink-100/50 dark:hover:bg-white/5 transition-colors"
          >
            <Phone size={16} strokeWidth={1.75} />
          </a>
          {/* Только переключатель темы. Mode (Менеджер/Инженер) убран —
              непонятен обычному пользователю, дефолт "Менеджер" подходит всем. */}
          <span className="shrink-0">
            <ThemeToggle />
          </span>
          {/* CTA Проект — только на sm+. На md-lg прячем текст, оставляем стрелку */}
          <a
            href="/project"
            aria-label="Перейти к проекту целиком"
            className="group hidden sm:inline-flex items-center gap-1.5 px-3 lg:px-4 h-11 md:h-9 rounded-md bg-accent-500 text-ink-950 text-sm font-medium hover:bg-accent-400 transition-colors duration-base whitespace-nowrap shrink-0"
          >
            <span>Проект</span>
            <ArrowRight
              size={14}
              strokeWidth={2}
              className="transition-transform duration-base group-hover:translate-x-0.5"
            />
          </a>
          {/* Burger button — видим ВСЕГДА, не только на mobile. В navbar только
              3 ключевые ссылки, остальные доступны через drawer. relative + z-10
              чтобы соседние кнопки не перехватывали клик. */}
          <button
            ref={burgerRef}
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="Открыть меню"
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav"
            className="relative z-10 inline-flex shrink-0 items-center justify-center min-h-11 min-w-11 h-11 w-11 rounded-md border border-ink-300 dark:border-white/10 text-ink-700 dark:text-ink-50 hover:text-clover-700 dark:hover:text-accent-500 hover:border-clover-500/60 dark:hover:border-accent-500/50 transition-colors"
          >
            <Menu size={20} strokeWidth={1.75} />
          </button>
        </div>
      </div>

    </header>

    {/* Drawer вынесен ИЗ <header> — sticky-родитель с backdrop-blur
        создаёт containing block для fixed-children (баг WebKit/Blink),
        что заставляло drawer схлопываться до высоты header (~109px). */}
      {mobileOpen && (
        <div
          ref={drawerRef}
          id="mobile-nav"
          role="dialog"
          aria-modal="true"
          aria-label="Меню"
          className="fixed inset-0 z-50"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-ink-950/80 backdrop-blur-sm"
            onClick={closeMobile}
            aria-hidden="true"
          />
          {/* Panel — адаптивный к теме (раньше всегда был тёмным, на light-сайте
              выглядело несогласованно: белая страница + чёрный drawer) */}
          <div className="absolute right-0 top-0 h-full w-[min(20rem,85vw)] bg-white dark:bg-ink-950 border-l border-ink-200 dark:border-white/10 shadow-2xl flex flex-col">
            <div className="flex items-center justify-between h-16 px-5 border-b border-ink-200 dark:border-white/10">
              <span className="font-display font-semibold text-ink-900 dark:text-ink-50 text-sm tracking-wide uppercase">
                Меню
              </span>
              <button
                type="button"
                onClick={closeMobile}
                aria-label="Закрыть меню"
                className="inline-flex items-center justify-center h-11 w-11 rounded-md text-ink-700 dark:text-ink-50 hover:text-clover-700 dark:hover:text-accent-500 transition-colors"
              >
                <X size={20} strokeWidth={1.75} />
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto py-2">
              {NAV_LINKS.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  onClick={closeMobile}
                  className={clsx(
                    "flex items-center gap-3 px-5 h-12 text-base transition-colors",
                    link.primary
                      ? "text-clover-700 dark:text-accent-500 font-medium hover:bg-clover-50 dark:hover:bg-white/5"
                      : "text-ink-700 dark:text-ink-200 hover:text-ink-900 dark:hover:text-ink-50 hover:bg-ink-100 dark:hover:bg-white/5",
                  )}
                >
                  {link.label}
                </a>
              ))}
              {/* Donate link отдельно — со специальной clover-стилизацией.
                  Выделена сильнее остальных пунктов: bg + border + larger font-weight. */}
              <a
                href="/#donate"
                onClick={closeMobile}
                className="mt-3 mx-3 flex items-center gap-3 px-4 h-12 text-base font-semibold rounded-md bg-clover-500 dark:bg-clover-600 text-white border-2 border-clover-600 dark:border-clover-500 hover:bg-clover-600 dark:hover:bg-clover-500 transition-colors shadow-sm"
              >
                <Heart size={18} strokeWidth={2.5} className="fill-white/30" aria-hidden="true" />
                <span>Поддержать автора</span>
                <span className="ml-auto text-sm font-normal opacity-80" aria-hidden="true">→</span>
              </a>
            </nav>
            <div className="border-t border-ink-200 dark:border-white/10 p-5">
              <a
                href="tel:+78002224457"
                onClick={closeMobile}
                className="flex items-center gap-2 text-ink-700 dark:text-ink-50 text-sm font-mono hover:text-clover-700 dark:hover:text-accent-500 transition-colors min-h-11"
              >
                <Phone size={16} strokeWidth={1.75} />
                8 (800) 222-44-57
              </a>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
