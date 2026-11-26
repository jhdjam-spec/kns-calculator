"use client";

/**
 * Cmd+K Command Palette — Linear/Vercel-style.
 *
 * Открытие: Cmd+K / Ctrl+K (или клик по кнопке в SiteNav).
 * Закрытие: Esc / клик по backdrop.
 * 4 группы:
 *   1. Действия — «Новый расчёт», «Скачать DOCX», «Переключить тему»
 *   2. Навигация — все маршруты сайта
 *   3. Энциклопедия — 7 теоретических разделов
 *   4. Поиск насосов (fuzzy через fuse.js по PumpsDB)
 *
 * Производительность: fuse-index лениво создаётся только при первом открытии.
 * Без зависимости от backend — поиск работает офлайн по PUMP_COUNT константе
 * (без полной БД, чтобы не раздувать bundle).
 */
import { useEffect, useMemo, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import Fuse from "fuse.js";
import {
  Search,
  Calculator,
  BookOpen,
  ArrowRight,
  Settings,
  FileDown,
  Moon,
  Sun,
  Heart,
  Home,
  Building2,
  Droplets,
  Database,
  FileText,
  Sparkles,
  Zap,
} from "lucide-react";
import { PUMPS_INDEX, type PumpIndexItem } from "@/data/pumpsIndex";

interface CommandItem {
  id: string;
  label: string;
  hint?: string;
  shortcut?: string;
  icon?: typeof Home;
  action: () => void;
  group: "actions" | "nav" | "teach" | "pumps";
  keywords?: string[];
}

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const NAV_ITEMS: Array<{ label: string; path: string; icon: typeof Home; hint: string }> = [
  { label: "Главная — быстрый подбор", path: "/", icon: Home, hint: "Q-H расчёт за минуту" },
  { label: "Проект целиком", path: "/project/", icon: Building2, hint: "Все подсистемы за раз" },
  { label: "Ливнёвка", path: "/storm/minimal/", icon: Droplets, hint: "Расчёт по СП 32" },
  { label: "Резервуары и корпуса", path: "/tanks/", icon: Database, hint: "ПП-ёмкости и корпус КНС" },
  { label: "Импорт ТЗ", path: "/import/", icon: FileText, hint: "Парсинг PDF/DOCX/email" },
  { label: "Энциклопедия", path: "/teach/", icon: BookOpen, hint: "Справочник СП и ГОСТ" },
  { label: "Правовая информация", path: "/legal/", icon: FileText, hint: "Реквизиты, оферта, 152-ФЗ" },
];

const TEACH_TOPICS: Array<{ label: string; path: string; hint: string }> = [
  { label: "Гидравлика", path: "/teach/hydraulics/", hint: "Дарси-Вейсбаха, NPSH, потери" },
  { label: "Пожарная защита", path: "/teach/fire/", hint: "СП 8, СП 10, пожарный запас" },
  { label: "Водоснабжение", path: "/teach/water/", hint: "СП 30, СП 31, СНиП 2.04" },
  { label: "Электрика", path: "/teach/electrical/", hint: "ПУЭ, IP-классы, ATEX, VFD" },
  { label: "Конструктив", path: "/teach/structural/", hint: "СП 22, всплытие, грунты" },
  { label: "ЛОС / биология", path: "/teach/los/", hint: "БПК, ХПК, нитрификация" },
  { label: "Документация", path: "/teach/documentation/", hint: "РД, опросник, ТЗ" },
];

// Fuse-индекс по 494 насосам — лениво создаётся при первом открытии палитры,
// дальше переиспользуется. Threshold 0.4 — баланс между «слишком строгий»
// и «слишком размытый» для русско-латинских смешанных запросов (KAIQUAN/Pedrollo).
let fuseSingleton: Fuse<PumpIndexItem> | null = null;
function getPumpFuse(): Fuse<PumpIndexItem> {
  if (fuseSingleton) return fuseSingleton;
  fuseSingleton = new Fuse(PUMPS_INDEX, {
    keys: [
      { name: "brand", weight: 2 },
      { name: "model", weight: 2 },
      { name: "type", weight: 0.5 },
    ],
    threshold: 0.4,
    ignoreLocation: true,
    minMatchCharLength: 2,
  });
  return fuseSingleton;
}

// ТОП-популярные модели (показываются когда поле пустое и пользователь
// ещё не начал печатать). Это бытовой сегмент budget с реальной ценой.
const POPULAR_PUMPS_TOP = 6;

function pumpSubtitle(p: PumpIndexItem): string {
  const parts: string[] = [];
  if (p.Q != null && p.H != null) parts.push(`Q=${p.Q} H=${p.H}`);
  if (p.P != null) parts.push(`${p.P} кВт`);
  if (p.ex) parts.push("Ex");
  return parts.join(" · ");
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter();
  const [search, setSearch] = useState("");

  const go = useCallback(
    (path: string) => {
      onOpenChange(false);
      // Якорные ссылки — scroll, остальное — router.push
      if (path.startsWith("#")) {
        document.getElementById(path.slice(1))?.scrollIntoView({ behavior: "smooth" });
      } else {
        router.push(path);
      }
    },
    [router, onOpenChange],
  );

  const items: CommandItem[] = useMemo(() => {
    const list: CommandItem[] = [];

    // Actions
    list.push({
      id: "act:new-calc",
      label: "Новый расчёт",
      hint: "Открыть быстрый подбор насоса",
      icon: Calculator,
      group: "actions",
      keywords: ["расчёт", "подбор", "calc", "new"],
      action: () => go("/#calculator"),
    });
    list.push({
      id: "act:docx",
      label: "Скачать опросный лист DOCX",
      hint: "Пустой шаблон ТЗ",
      icon: FileDown,
      group: "actions",
      keywords: ["docx", "опросник", "тз", "шаблон", "скачать"],
      action: () => {
        onOpenChange(false);
        // Не используем backend сразу — открываем главную и юзер кликает там
        document.getElementById("hero")?.scrollIntoView({ behavior: "smooth" });
      },
    });
    list.push({
      id: "act:donate",
      label: "Поддержать автора",
      hint: "YooMoney fundraise",
      icon: Heart,
      group: "actions",
      keywords: ["donate", "поддержать", "донат", "yoomoney"],
      action: () => go("/#donate"),
    });
    list.push({
      id: "act:theme",
      label: "Переключить тему",
      hint: "Светлая / тёмная",
      shortcut: "⌘\\",
      icon: typeof window !== "undefined" && document.documentElement.classList.contains("dark") ? Sun : Moon,
      group: "actions",
      keywords: ["theme", "тема", "dark", "light", "тёмная", "светлая"],
      action: () => {
        const html = document.documentElement;
        const current = html.classList.contains("dark");
        if (current) {
          html.classList.remove("dark");
          html.classList.add("light");
          localStorage.setItem("theme", "light");
        } else {
          html.classList.add("dark");
          html.classList.remove("light");
          localStorage.setItem("theme", "dark");
        }
        onOpenChange(false);
      },
    });
    list.push({
      id: "act:settings",
      label: "Настройки",
      hint: "В разработке",
      icon: Settings,
      group: "actions",
      keywords: ["settings", "настройки", "config"],
      action: () => {
        onOpenChange(false);
      },
    });

    // Navigation
    NAV_ITEMS.forEach((n) =>
      list.push({
        id: `nav:${n.path}`,
        label: n.label,
        hint: n.hint,
        icon: n.icon,
        group: "nav",
        action: () => go(n.path),
      }),
    );

    // Teach topics
    TEACH_TOPICS.forEach((t) =>
      list.push({
        id: `teach:${t.path}`,
        label: t.label,
        hint: t.hint,
        icon: Sparkles,
        group: "teach",
        action: () => go(t.path),
      }),
    );

    return list;
  }, [go, onOpenChange]);

  // Насосы: либо ТОП-популярных при пустом поиске, либо результаты fuse.js
  const pumpResults: PumpIndexItem[] = useMemo(() => {
    const query = search.trim();
    if (query.length < 2) {
      return PUMPS_INDEX.slice(0, POPULAR_PUMPS_TOP);
    }
    return getPumpFuse()
      .search(query, { limit: 8 })
      .map((r) => r.item);
  }, [search]);

  // Cmd+K глобальный shortcut
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpenChange(!open);
      }
      // Cmd+\ — переключение темы
      if ((e.metaKey || e.ctrlKey) && e.key === "\\") {
        e.preventDefault();
        const html = document.documentElement;
        if (html.classList.contains("dark")) {
          html.classList.remove("dark");
          html.classList.add("light");
          localStorage.setItem("theme", "light");
        } else {
          html.classList.add("dark");
          html.classList.remove("light");
          localStorage.setItem("theme", "dark");
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  // Lock body scroll while open
  useEffect(() => {
    if (open) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [open]);

  if (!open) return null;

  const grouped = items.reduce<Record<string, CommandItem[]>>((acc, item) => {
    acc[item.group] = acc[item.group] ?? [];
    acc[item.group].push(item);
    return acc;
  }, {});

  const groupLabels: Record<string, string> = {
    actions: "Действия",
    nav: "Навигация",
    teach: "Энциклопедия",
    pumps: "Насосы",
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center pt-[10vh] px-4"
      onClick={() => onOpenChange(false)}
      role="dialog"
      aria-modal="true"
      aria-label="Командная палитра"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-ink-950/70 backdrop-blur-sm animate-in fade-in duration-200"
        aria-hidden="true"
      />

      {/* Palette */}
      <Command
        className="relative w-full max-w-2xl rounded-xl bg-surface dark:bg-ink-900 border border-border dark:border-white/10 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        label="Поиск команды"
      >
        <div className="flex items-center gap-3 px-4 border-b border-border dark:border-white/10">
          <Search size={18} strokeWidth={1.75} className="text-ink-400 dark:text-ink-500 shrink-0" />
          <Command.Input
            value={search}
            onValueChange={setSearch}
            placeholder="Поиск действий, страниц, разделов…"
            className="flex-1 h-12 bg-transparent text-foreground dark:text-ink-50 placeholder:text-ink-400 dark:placeholder:text-ink-500 outline-none text-sm"
            autoFocus
          />
          <kbd className="hidden sm:inline-block text-[10px] font-mono uppercase tracking-wider text-ink-500 dark:text-ink-400 border border-ink-200 dark:border-white/10 rounded px-1.5 py-0.5">
            Esc
          </kbd>
        </div>

        <Command.List className="max-h-[60vh] overflow-y-auto p-2">
          <Command.Empty className="py-8 text-center text-sm text-muted dark:text-ink-500">
            Ничего не найдено.
          </Command.Empty>

          {Object.entries(grouped).map(([group, list]) => (
            <Command.Group
              key={group}
              heading={
                <div className="px-2 py-1.5 text-[10px] font-mono uppercase tracking-wider text-muted dark:text-ink-500">
                  {groupLabels[group] ?? group}
                </div>
              }
            >
              {list.map((item) => {
                const Icon = item.icon ?? ArrowRight;
                return (
                  <Command.Item
                    key={item.id}
                    value={[item.label, item.hint, ...(item.keywords ?? [])].filter(Boolean).join(" ")}
                    onSelect={() => item.action()}
                    className="group flex items-center gap-3 px-2 py-2 rounded-md text-sm cursor-pointer data-[selected=true]:bg-clover-50 dark:data-[selected=true]:bg-clover-900/30 transition-colors"
                  >
                    <Icon
                      size={16}
                      strokeWidth={1.75}
                      className="shrink-0 text-ink-500 dark:text-ink-400 group-data-[selected=true]:text-clover-600 dark:group-data-[selected=true]:text-clover-300"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-foreground dark:text-ink-100 truncate">
                        {item.label}
                      </div>
                      {item.hint && (
                        <div className="text-xs text-muted dark:text-ink-500 truncate">
                          {item.hint}
                        </div>
                      )}
                    </div>
                    {item.shortcut && (
                      <kbd className="hidden sm:inline-block text-[10px] font-mono uppercase text-ink-500 dark:text-ink-400 border border-ink-200 dark:border-white/10 rounded px-1.5 py-0.5">
                        {item.shortcut}
                      </kbd>
                    )}
                  </Command.Item>
                );
              })}
            </Command.Group>
          ))}

          {/* Насосы — fuse.js fuzzy-поиск по 494 моделям. Свой Group с ручной
              фильтрацией, поэтому value=item.label чтобы cmdk не отбрасывал. */}
          {pumpResults.length > 0 && (
            <Command.Group
              heading={
                <div className="flex items-center justify-between px-2 py-1.5 text-[10px] font-mono uppercase tracking-wider text-muted dark:text-ink-500">
                  <span>
                    {search.trim().length < 2 ? "Популярные насосы" : `Насосы (${pumpResults.length})`}
                  </span>
                  <span className="text-ink-400/60 dark:text-ink-500/60">из {PUMPS_INDEX.length}</span>
                </div>
              }
            >
              {pumpResults.map((p) => {
                const subtitle = pumpSubtitle(p);
                return (
                  <Command.Item
                    key={`pump:${p.id}`}
                    value={`pump ${p.brand} ${p.model} ${p.type} ${search}`}
                    onSelect={() => {
                      onOpenChange(false);
                      try {
                        sessionStorage.setItem(
                          `pump:${p.id}`,
                          JSON.stringify({ Q: p.Q, H: p.H }),
                        );
                      } catch {
                        // sessionStorage недоступен (Private Mode, quota) — ничего
                      }
                      const q = p.Q != null ? `q=${p.Q}&` : "";
                      const h = p.H != null ? `h=${p.H}&` : "";
                      router.push(
                        `/?${q}${h}pump=${encodeURIComponent(p.id)}#calculator`,
                      );
                    }}
                    className="group flex items-center gap-3 px-2 py-2 rounded-md text-sm cursor-pointer data-[selected=true]:bg-clover-50 dark:data-[selected=true]:bg-clover-900/30 transition-colors"
                  >
                    <Zap
                      size={16}
                      strokeWidth={1.75}
                      className="shrink-0 text-ink-500 dark:text-ink-400 group-data-[selected=true]:text-clover-600 dark:group-data-[selected=true]:text-clover-300"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-foreground dark:text-ink-100 truncate">
                        <span className="font-medium">{p.brand}</span>{" "}
                        <span className="text-ink-600 dark:text-ink-300">{p.model}</span>
                      </div>
                      {subtitle && (
                        <div className="text-xs text-muted dark:text-ink-500 truncate">
                          {subtitle}
                        </div>
                      )}
                    </div>
                    {p.price && (
                      <span className="hidden sm:inline-block text-[10px] font-mono text-ink-500 dark:text-ink-400 shrink-0">
                        {p.price.toLocaleString("ru-RU")} ₽
                      </span>
                    )}
                  </Command.Item>
                );
              })}
            </Command.Group>
          )}
        </Command.List>

        {/* Footer hint */}
        <div className="flex items-center justify-between gap-2 px-4 py-2 border-t border-border dark:border-white/10 text-[11px] font-mono text-muted dark:text-ink-500">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1">
              <kbd className="border border-ink-200 dark:border-white/10 rounded px-1">↑↓</kbd>
              навигация
            </span>
            <span className="inline-flex items-center gap-1">
              <kbd className="border border-ink-200 dark:border-white/10 rounded px-1">⏎</kbd>
              выбрать
            </span>
          </div>
          <span className="hidden sm:inline-flex items-center gap-1">
            <kbd className="border border-ink-200 dark:border-white/10 rounded px-1">⌘K</kbd>
            закрыть
          </span>
        </div>
      </Command>
    </div>
  );
}
