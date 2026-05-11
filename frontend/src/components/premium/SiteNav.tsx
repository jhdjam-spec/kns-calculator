"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Phone, Menu, X } from "lucide-react";
import clsx from "clsx";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ModeToggle } from "@/components/providers/ModeToggle";

const NAV_LINKS: Array<{ href: string; label: string; primary?: boolean }> = [
  { href: "/project", label: "Проект целиком", primary: true },
  { href: "/storm/minimal", label: "Ливнёвка" },
  { href: "/tanks", label: "Резервуары" },
  { href: "/teach", label: "Энциклопедия" },
  { href: "/import", label: "Импорт ТЗ" },
  { href: "#calculator", label: "Быстрый подбор" },
  { href: "#faq", label: "FAQ" },
];

export function SiteNav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 80);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Close mobile menu on Esc
  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileOpen(false);
    };
    window.addEventListener("keydown", onKey);
    // Lock body scroll while drawer open
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [mobileOpen]);

  const closeMobile = () => setMobileOpen(false);

  return (
    <header
      className={clsx(
        // sticky top-0: висит под BetaBanner (BetaBanner static, не перекрывает на mobile).
        "sticky top-0 z-40 transition-all duration-base ease-out-quart",
        scrolled
          ? "h-14 bg-ink-950/85 backdrop-blur-md backdrop-saturate-150 border-b border-white/[0.06]"
          : "h-16 md:h-[72px] bg-ink-950/40 backdrop-blur-sm",
      )}
    >
      <div className="max-w-7xl mx-auto h-full px-5 md:px-10 flex items-center justify-between">
        <a href="#hero" className="flex items-center gap-3 group min-h-11">
          <div className="relative size-8 rounded-md bg-accent-500 flex items-center justify-center shrink-0">
            <span className="font-display font-bold text-ink-950 text-sm">И·С</span>
          </div>
          <div className="leading-tight">
            <span className="font-display font-semibold text-ink-50 text-sm tracking-wide uppercase">
              ИНСЕРВО
            </span>
            <span className="ml-1.5 text-ink-400 text-xs font-mono hidden sm:inline">· Серво-Юг</span>
          </div>
        </a>

        <nav className="hidden lg:flex items-center gap-6 text-sm text-ink-300">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className={clsx(
                "transition-colors duration-fast",
                link.primary
                  ? "hover:text-accent-500 font-medium"
                  : "hover:text-ink-50",
              )}
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2 md:gap-3">
          {/* Desktop phone (full format) */}
          <a
            href="tel:+78002224457"
            className="hidden md:flex items-center gap-2 text-ink-50 text-sm font-mono hover:text-accent-500 transition-colors min-h-11"
          >
            <Phone size={14} strokeWidth={1.75} />
            8 (800) 222-44-57
          </a>
          {/* Mobile phone (icon + short format) */}
          <a
            href="tel:+78002224457"
            aria-label="Позвонить 8 800 222 44 57"
            className="md:hidden inline-flex items-center justify-center gap-1.5 h-11 px-2.5 rounded-md text-ink-50 text-xs font-mono hover:text-accent-500 transition-colors"
          >
            <Phone size={16} strokeWidth={1.75} />
            <span>8-800</span>
          </a>
          {/* Mode toggle — Менеджер / Инженер. На < sm рисует М / И. */}
          <ModeToggle compact />
          <ThemeToggle />
          <a
            href="/project"
            className="group hidden sm:inline-flex items-center gap-1.5 px-4 h-11 md:h-9 rounded-md bg-accent-500 text-ink-950 text-sm font-medium hover:bg-accent-400 transition-colors duration-base"
          >
            <span className="hidden sm:inline">Проект</span>
            <ArrowRight
              size={14}
              strokeWidth={2}
              className="transition-transform duration-base group-hover:translate-x-0.5"
            />
          </a>
          {/* Burger button — visible only < lg */}
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="Открыть меню"
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav"
            className="lg:hidden inline-flex items-center justify-center h-11 w-11 rounded-md border border-white/10 text-ink-50 hover:text-accent-500 hover:border-accent-500/50 transition-colors"
          >
            <Menu size={20} strokeWidth={1.75} />
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div
          id="mobile-nav"
          role="dialog"
          aria-modal="true"
          aria-label="Меню"
          className="lg:hidden fixed inset-0 z-50"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-ink-950/80 backdrop-blur-sm"
            onClick={closeMobile}
            aria-hidden="true"
          />
          {/* Panel */}
          <div className="absolute right-0 top-0 h-full w-[min(20rem,85vw)] bg-ink-950 border-l border-white/10 shadow-2xl flex flex-col">
            <div className="flex items-center justify-between h-16 px-5 border-b border-white/10">
              <span className="font-display font-semibold text-ink-50 text-sm tracking-wide uppercase">
                Меню
              </span>
              <button
                type="button"
                onClick={closeMobile}
                aria-label="Закрыть меню"
                className="inline-flex items-center justify-center h-11 w-11 rounded-md text-ink-50 hover:text-accent-500 transition-colors"
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
                      ? "text-accent-500 font-medium hover:bg-white/5"
                      : "text-ink-200 hover:text-ink-50 hover:bg-white/5",
                  )}
                >
                  {link.label}
                </a>
              ))}
            </nav>
            <div className="border-t border-white/10 p-5">
              <a
                href="tel:+78002224457"
                onClick={closeMobile}
                className="flex items-center gap-2 text-ink-50 text-sm font-mono hover:text-accent-500 transition-colors min-h-11"
              >
                <Phone size={16} strokeWidth={1.75} />
                8 (800) 222-44-57
              </a>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
