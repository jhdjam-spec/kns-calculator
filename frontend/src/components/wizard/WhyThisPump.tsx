"use client";

/**
 * WhyThisPump — drawer-объяснение подбора одного насоса.
 *
 * Источник: `pump.score_explanation` (backend matching.py::build_score_explanation).
 * Содержит 5 шагов + 5 композит-факторов с hint_engineer/hint_manager.
 *
 * Mode-aware: useMode() → выбираем engineer vs manager hint.
 *
 * Открывается по клику «Почему этот?» в карточке насоса.
 */
import { X } from "lucide-react";
import { useEffect, useId } from "react";
import { useMode } from "@/components/providers/ModeProvider";
import type { PumpResult } from "@/schemas/result";

export interface WhyThisPumpProps {
  pump: PumpResult;
  open: boolean;
  onClose: () => void;
}

interface CompositeFactor {
  value?: number;
  weight?: number;
  contribution?: number;
  label?: string;
  hint_engineer?: string;
  hint_manager?: string;
}

interface Citation {
  text?: string;
  url?: string;
}

export function WhyThisPump({ pump, open, onClose }: WhyThisPumpProps) {
  const { mode } = useMode();
  const titleId = useId();

  // ESC закрывает drawer
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const ex = pump.score_explanation || {};
  const step1 = (ex.step_1_filter as string) || "";
  const step2 = (ex.step_2_envelope as string) || "";
  const step3 = (ex.step_3_aor as string) || "";
  const step5 = (ex.step_5_segment as string) || "";
  const composite = (ex.step_4_composite as Record<string, CompositeFactor>) || {};
  const compositeSum = (ex.step_4_composite_sum as number) ?? null;
  const finalScore = (ex.step_4_final_score as number) ?? pump.score;
  const rank = (ex.rank_in_segment as number | null) ?? null;
  const total = (ex.candidates_in_segment as number | null) ?? null;
  const citations = (ex.citations as Citation[]) || [];

  const factors = Object.entries(composite);
  const maxContribution = Math.max(
    ...factors.map(([, f]) => f.contribution ?? 0),
    0.001,
  );

  const isEngineer = mode === "engineer";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      data-testid="why-this-pump"
      className="fixed inset-0 z-50 flex justify-end"
    >
      {/* Backdrop */}
      <button
        type="button"
        aria-label="Закрыть"
        onClick={onClose}
        className="absolute inset-0 bg-ink-950/60 backdrop-blur-sm transition-opacity duration-200"
      />

      {/* Sidebar */}
      <aside
        className="relative w-full max-w-xl h-full bg-white shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-300"
      >
        <header className="sticky top-0 bg-white border-b border-ink-200 px-6 py-4 flex items-center justify-between z-10">
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-ink-500">
              Почему этот насос?
            </div>
            <h3 id={titleId} className="font-display text-xl font-semibold text-ink-950">
              {pump.brand} {pump.model}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
            className="rounded-md p-2 hover:bg-ink-100 transition-colors"
          >
            <X size={20} strokeWidth={1.75} />
          </button>
        </header>

        <div className="px-6 py-5 space-y-5">
          {/* Финальная сводка */}
          <section className="rounded-card bg-accent-500/5 border border-accent-500/30 p-4">
            <div className="text-xs font-mono uppercase tracking-wider text-ink-500 mb-1">
              Итоговый score
            </div>
            <div className="font-display text-3xl font-semibold text-ink-950 tabular-nums">
              {(finalScore * 100).toFixed(1)}%
            </div>
            {rank !== null && total !== null && (
              <div className="text-sm text-ink-600 mt-1">
                #{rank} из {total} кандидатов в сегменте
              </div>
            )}
            {compositeSum !== null && Math.abs(compositeSum - finalScore) > 0.01 && (
              <div className="text-xs text-ink-500 mt-2">
                Композит до штрафов и не-стационарных факторов: {(compositeSum * 100).toFixed(1)}%
              </div>
            )}
          </section>

          {/* Шаги 1-5 */}
          <section data-testid="why-steps">
            <h4 className="text-sm font-mono uppercase tracking-wider text-ink-500 mb-3">
              Шаги подбора
            </h4>
            <ol className="space-y-2">
              <Step n={1} title="Фильтр по типу стоков" body={step1} />
              <Step n={2} title="Q-H envelope" body={step2} />
              <Step n={3} title="POR / AOR" body={step3} />
              <Step n={4} title="Композитный score" body={`Сумма по 5 факторам (см. ниже).`} />
              {step5 && <Step n={5} title="Выбор сегмента" body={step5} />}
            </ol>
          </section>

          {/* Композит-факторы (bar chart) */}
          {factors.length > 0 && (
            <section data-testid="why-factors">
              <h4 className="text-sm font-mono uppercase tracking-wider text-ink-500 mb-3">
                Композитные факторы
              </h4>
              <ul className="space-y-3">
                {factors.map(([key, f]) => {
                  const contribution = f.contribution ?? 0;
                  const widthPct = (contribution / maxContribution) * 100;
                  const hint = isEngineer ? f.hint_engineer : f.hint_manager;
                  return (
                    <li key={key} data-factor={key}>
                      <div className="flex items-baseline justify-between mb-1 gap-2">
                        <span className="text-sm font-medium text-ink-900">
                          {f.label || key}
                        </span>
                        <span className="text-xs font-mono text-ink-600 tabular-nums">
                          {(f.value ?? 0).toFixed(2)} × {((f.weight ?? 0) * 100).toFixed(0)}%
                          {" "}= <strong>{contribution.toFixed(3)}</strong>
                        </span>
                      </div>
                      <div
                        className="h-2 rounded-full bg-ink-100 overflow-hidden"
                        aria-label={`${f.label || key}: вклад ${contribution.toFixed(3)}`}
                      >
                        <div
                          className="h-full bg-accent-500 transition-all"
                          // SVG/style: процентная ширина не выражается tailwind-классом
                          // eslint-disable-next-line react/forbid-dom-props
                          style={{ width: `${widthPct}%` }}
                        />
                      </div>
                      {hint && (
                        <p className="text-xs text-ink-600 mt-1.5">{hint}</p>
                      )}
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {/* Цитаты СП/ГОСТ */}
          {citations.length > 0 && (
            <section data-testid="why-citations">
              <h4 className="text-sm font-mono uppercase tracking-wider text-ink-500 mb-2">
                Источники
              </h4>
              <ul className="text-sm text-ink-700 space-y-1.5">
                {citations.map((c, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-accent-500">·</span>
                    {c.url ? (
                      <a
                        href={c.url}
                        target="_blank"
                        rel="noreferrer"
                        className="underline decoration-dotted hover:text-accent-600"
                      >
                        {c.text || c.url}
                      </a>
                    ) : (
                      <span>{c.text}</span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Mode hint */}
          <div className="text-xs text-ink-500 italic pt-2 border-t border-ink-200">
            Тексты подобраны для режима{" "}
            <strong>{isEngineer ? "👷 Инженер" : "💼 Менеджер ОП"}</strong>. Переключить —
            тумблер «Режим» в шапке.
          </div>
        </div>
      </aside>
    </div>
  );
}

function Step({ n, title, body }: { n: number; title: string; body: string }) {
  if (!body) return null;
  return (
    <li className="flex gap-3" data-step={n}>
      <div className="flex-shrink-0 size-7 rounded-full bg-ink-900 text-ink-50 text-xs font-mono font-medium flex items-center justify-center">
        {n}
      </div>
      <div className="pt-0.5">
        <div className="text-sm font-medium text-ink-950">{title}</div>
        <p className="text-sm text-ink-600 mt-0.5 leading-snug">{body}</p>
      </div>
    </li>
  );
}
