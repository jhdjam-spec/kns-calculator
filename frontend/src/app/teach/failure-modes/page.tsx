// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO — Библиотека типовых отказов КНС/НС                            │
// │ /teach/failure-modes — 26 режимов с фильтрами по категории/severity   │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";
import { SiteNav } from "@/components/premium/SiteNav";
import { SiteFooter } from "@/components/premium/SiteFooter";
import {
  failureModesApi,
  type FailureMode,
  type FailureModesListResponse,
} from "@/lib/api-extended";

const SEVERITIES: Array<{ key: FailureMode["severity"]; label: string; cls: string }> = [
  { key: "low", label: "Низкая", cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
  { key: "medium", label: "Средняя", cls: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  { key: "high", label: "Высокая", cls: "bg-orange-500/15 text-orange-300 border-orange-500/30" },
  { key: "critical", label: "Критическая", cls: "bg-red-500/15 text-red-300 border-red-500/30" },
];

const CATEGORY_LABEL: Record<string, string> = {
  hydraulic: "Гидравлика",
  mechanical: "Механика",
  electrical: "Электрика",
  operational: "Эксплуатация",
  environmental: "Окружающая среда",
};

const CATEGORY_ICON: Record<string, string> = {
  hydraulic: "💧",
  mechanical: "⚙️",
  electrical: "⚡",
  operational: "🛠",
  environmental: "🌡",
};

function severityMeta(s: string) {
  return SEVERITIES.find((x) => x.key === s) ?? SEVERITIES[1];
}

export default function FailureModesPage() {
  const [list, setList] = useState<FailureModesListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [category, setCategory] = useState<string>("");
  const [severity, setSeverity] = useState<string>("");
  const [selected, setSelected] = useState<FailureMode | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    failureModesApi
      .list({
        category: category || undefined,
        severity: severity || undefined,
      })
      .then((res) => {
        if (!cancelled) {
          setList(res);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(String(e));
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [category, severity]);

  const categories = useMemo(() => list?.categories ?? [], [list]);

  return (
    <>
      <SiteNav />
      <main
        id="main"
        className="min-h-screen bg-ink-50 dark:bg-ink-950 px-5 md:px-10 pt-24 md:pt-28 pb-10"
      >
        <div className="max-w-7xl mx-auto">
          <div className="mb-8 flex items-center justify-between">
            <h1 className="text-sm font-mono uppercase tracking-wider text-ink-600 dark:text-ink-500">
              INSERVO · Энциклопедия / Типовые отказы
            </h1>
            <a
              href="/teach"
              className="text-sm text-ink-700 dark:text-ink-400 hover:text-brand-700 dark:hover:text-accent-500 transition-colors"
            >
              ← К темам
            </a>
          </div>

          <div className="mb-8 max-w-3xl">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-ink-900 dark:text-ink-50 mb-4">
              Типовые отказы КНС/НС
            </h2>
            <p className="text-ink-700 dark:text-ink-400 leading-relaxed">
              Образовательный каталог 26 режимов отказа: симптомы, причины,
              профилактика, стоимость устранения, downtime. Основан на СП 32,
              СП 30, ГОСТ Р 53674, ПУЭ, IEC 60079 + 30-летний опыт INSERVO.
            </p>
          </div>

          {/* Фильтры */}
          <div
            className="mb-6 flex flex-wrap items-center gap-3"
            data-testid="failure-filters"
          >
            <label className="text-xs font-mono uppercase tracking-wider text-ink-600 dark:text-ink-500">
              Категория:
            </label>
            <select
              aria-label="Категория"
              className="form-input bg-white border-ink-200 text-ink-900 dark:bg-ink-900 dark:border-ink-800 dark:text-ink-100 text-sm"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="">Все категории</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {CATEGORY_ICON[c] || "·"} {CATEGORY_LABEL[c] || c}
                </option>
              ))}
            </select>

            <label className="text-xs font-mono uppercase tracking-wider text-ink-600 dark:text-ink-500 ml-3">
              Severity:
            </label>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => setSeverity("")}
                className={
                  severity === ""
                    ? "px-3 py-1 text-xs rounded-md bg-brand-700 text-white dark:bg-ink-50 dark:text-ink-950 font-medium"
                    : "px-3 py-1 text-xs rounded-md bg-white text-ink-700 border border-ink-200 hover:border-brand-400 dark:bg-ink-900 dark:text-ink-300 dark:border-ink-800 dark:hover:border-ink-700"
                }
              >
                Все
              </button>
              {SEVERITIES.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  onClick={() => setSeverity(s.key === severity ? "" : s.key)}
                  data-testid={`severity-${s.key}`}
                  className={
                    severity === s.key
                      ? `px-3 py-1 text-xs rounded-md border ${s.cls}`
                      : "px-3 py-1 text-xs rounded-md bg-white text-ink-700 border border-ink-200 hover:border-brand-400 dark:bg-ink-900 dark:text-ink-300 dark:border-ink-800 dark:hover:border-ink-700"
                  }
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {loading && (
            <div className="text-ink-700 dark:text-ink-400" data-testid="failure-loading">
              Загрузка каталога…
            </div>
          )}
          {error && (
            <div className="rounded-md bg-red-50 border border-red-200 dark:bg-red-950/40 dark:border-red-700 p-3 text-red-700 dark:text-red-300 text-sm">
              Ошибка: {error}
            </div>
          )}

          {list && !loading && (
            <>
              <div className="text-xs text-ink-600 dark:text-ink-500 mb-3">
                Найдено: {list.count} режимов
              </div>
              <div
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
                data-testid="failure-grid"
              >
                {list.modes.map((m) => (
                  <ModeCard key={m.id} mode={m} onOpen={() => setSelected(m)} />
                ))}
              </div>
              {list.modes.length === 0 && (
                <div className="text-ink-600 dark:text-ink-500 italic">
                  Нет отказов под текущие фильтры.
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {selected && <ModeDrawer mode={selected} onClose={() => setSelected(null)} />}
      <SiteFooter />
    </>
  );
}

function ModeCard({ mode, onOpen }: { mode: FailureMode; onOpen: () => void }) {
  const sev = severityMeta(mode.severity);
  return (
    <button
      type="button"
      onClick={onOpen}
      data-testid={`mode-card-${mode.id}`}
      className="text-left flex flex-col p-5 bg-white border border-ink-200 dark:bg-ink-900 dark:border-ink-800 rounded-lg hover:border-brand-400 dark:hover:border-accent-500/50 transition-colors group shadow-premium-sm"
    >
      <div className="flex items-baseline justify-between mb-3">
        <span className="text-lg" aria-hidden>
          {CATEGORY_ICON[mode.category] || "•"}
        </span>
        <span
          className={`text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full border ${sev.cls}`}
        >
          {sev.label}
        </span>
      </div>
      <div className="font-display font-semibold text-ink-900 dark:text-ink-50 group-hover:text-brand-700 dark:group-hover:text-accent-500 transition-colors mb-2">
        {mode.name}
      </div>
      <div className="text-xs font-mono uppercase tracking-wider text-ink-600 dark:text-ink-500 mb-2">
        {CATEGORY_LABEL[mode.category] || mode.category}
      </div>
      <ul className="text-sm text-ink-700 dark:text-ink-400 space-y-0.5 mt-1">
        {mode.symptoms.slice(0, 3).map((s, i) => (
          <li key={i} className="flex gap-1.5">
            <span className="text-brand-600 dark:text-accent-500/70 shrink-0">·</span>
            <span className="line-clamp-2">{s}</span>
          </li>
        ))}
      </ul>
      {mode.trigger_in_calculator && (
        <div className="mt-3 pt-3 border-t border-ink-200 dark:border-ink-800 text-xs text-ink-600 dark:text-ink-500">
          Связан с триггером: <code className="text-brand-700 dark:text-accent-500/80">{mode.trigger_in_calculator}</code>
        </div>
      )}
    </button>
  );
}

function ModeDrawer({ mode, onClose }: { mode: FailureMode; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const sev = severityMeta(mode.severity);
  const [fixLow, fixHigh] = mode.fix_cost_rub;
  const [downLow, downHigh] = mode.downtime_hours;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={mode.name}
      data-testid="failure-drawer"
      className="fixed inset-0 z-50 flex justify-end"
    >
      <button
        type="button"
        aria-label="Закрыть"
        onClick={onClose}
        className="absolute inset-0 bg-ink-950/70 backdrop-blur-sm"
      />
      <aside className="relative w-full max-w-xl h-full bg-ink-950 border-l border-ink-800 shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-300">
        <header className="sticky top-0 bg-ink-950 border-b border-ink-800 px-6 py-4 flex items-start justify-between z-10">
          <div className="pr-3">
            <div className="text-xs font-mono uppercase tracking-wider text-ink-500 mb-1">
              {CATEGORY_ICON[mode.category]} {CATEGORY_LABEL[mode.category] || mode.category}
            </div>
            <h3 className="font-display text-xl font-semibold text-ink-50">{mode.name}</h3>
            <span
              className={`mt-2 inline-block text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full border ${sev.cls}`}
            >
              {sev.label}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
            className="rounded-md p-2 hover:bg-ink-900 transition-colors text-ink-300"
          >
            <X size={20} strokeWidth={1.75} />
          </button>
        </header>

        <div className="px-6 py-5 space-y-5 text-ink-300">
          <Section title="Симптомы" items={mode.symptoms} />
          <Section title="Причины" items={mode.causes} />
          <Section title="Профилактика" items={mode.prevention} />

          <div className="grid grid-cols-2 gap-3">
            <Stat label="Стоимость ремонта" value={`${formatRub(fixLow)} – ${formatRub(fixHigh)} ₽`} />
            <Stat label="Downtime" value={`${downLow} – ${downHigh} ч`} />
          </div>

          {mode.lifecycle_impact && (
            <div>
              <h4 className="text-xs font-mono uppercase tracking-wider text-ink-500 mb-1">
                Влияние на ресурс
              </h4>
              <p className="text-sm text-ink-300 leading-relaxed">{mode.lifecycle_impact}</p>
            </div>
          )}

          <div className="pt-2 border-t border-ink-800 text-xs text-ink-500 space-y-1">
            {mode.sp_norm && (
              <div>
                Нормативная база: <code className="text-accent-500/80">{mode.sp_norm}</code>
              </div>
            )}
            {mode.trigger_in_calculator && (
              <div>
                Триггер в калькуляторе:{" "}
                <code className="text-accent-500/80">{mode.trigger_in_calculator}</code>
              </div>
            )}
            <div>ID: <code>{mode.id}</code></div>
          </div>
        </div>
      </aside>
    </div>
  );
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <h4 className="text-xs font-mono uppercase tracking-wider text-ink-500 mb-2">
        {title}
      </h4>
      <ul className="text-sm space-y-1.5">
        {items.map((it, i) => (
          <li key={i} className="flex gap-2">
            <span className="text-accent-500/70 shrink-0">·</span>
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-ink-900 border border-ink-800 p-3">
      <div className="text-[10px] font-mono uppercase tracking-wider text-ink-500 mb-0.5">
        {label}
      </div>
      <div className="font-display font-semibold text-ink-50 tabular-nums text-sm">
        {value}
      </div>
    </div>
  );
}

function formatRub(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)} млн`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)} тыс`;
  return new Intl.NumberFormat("ru-RU").format(n);
}
