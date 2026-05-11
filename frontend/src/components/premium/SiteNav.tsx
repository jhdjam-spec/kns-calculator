"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Phone } from "lucide-react";
import clsx from "clsx";
import { ThemeToggle } from "@/components/ThemeToggle";

export function SiteNav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 80);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

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
          <a href="/project" className="hover:text-accent-500 transition-colors duration-fast font-medium">
            Проект целиком
          </a>
          <a href="/storm/minimal" className="hover:text-ink-50 transition-colors duration-fast">
            Ливнёвка
          </a>
          <a href="/tanks" className="hover:text-ink-50 transition-colors duration-fast">
            Резервуары
          </a>
          <a href="/teach" className="hover:text-ink-50 transition-colors duration-fast">
            Энциклопедия
          </a>
          <a href="#calculator" className="hover:text-ink-50 transition-colors duration-fast">
            Быстрый подбор
          </a>
          <a href="#faq" className="hover:text-ink-50 transition-colors duration-fast">
            FAQ
          </a>
        </nav>

        <div className="flex items-center gap-2 md:gap-3">
          <a
            href="tel:+78002224457"
            className="hidden md:flex items-center gap-2 text-ink-50 text-sm font-mono hover:text-accent-500 transition-colors min-h-11"
          >
            <Phone size={14} strokeWidth={1.75} />
            8 (800) 222-44-57
          </a>
          <ThemeToggle />
          <a
            href="/project"
            className="group inline-flex items-center gap-1.5 px-4 h-11 md:h-9 rounded-md bg-accent-500 text-ink-950 text-sm font-medium hover:bg-accent-400 transition-colors duration-base"
          >
            <span className="hidden sm:inline">Проект</span>
            <span className="sm:hidden">К проекту</span>
            <ArrowRight
              size={14}
              strokeWidth={2}
              className="transition-transform duration-base group-hover:translate-x-0.5"
            />
          </a>
        </div>
      </div>
    </header>
  );
}
