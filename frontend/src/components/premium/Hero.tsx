"use client";

import { useState } from "react";
import { ArrowRight, FileDown, SlidersHorizontal } from "lucide-react";
import { useMode } from "@/components/providers/ModeProvider";

interface HeroProps {
  onCalculate: (Q_m3h: number) => void;
  isCalculating?: boolean;
}

/**
 * Скачивание пустого опросного листа DOCX через POST /handoff/empty-questionnaire-docx.
 * Один и тот же файл с двумя названиями:
 * — «Техзадание_КНС.docx» — для заказчика, формулировка через «техническое задание»
 * — «Опросный_лист_КНС.docx» — для инженера, формулировка через «опросный лист»
 */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api/backend";

async function downloadEmptyQuestionnaire(filename: string): Promise<void> {
  const res = await fetch(`${API_BASE}/handoff/empty-questionnaire-docx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    throw new Error(`Не удалось скачать форму (${res.status})`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Технический верхний потолок для Q в Hero — больше уже не наш профиль (магистрали).
// Если пользователь ввёл крупнее — показываем подсказку и предлагаем связаться.
const Q_HERO_MAX = 10000;

export function Hero({ onCalculate, isCalculating }: HeroProps) {
  const [qInput, setQInput] = useState("21.2");
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const { mode } = useMode();

  const qNumericRaw = parseFloat(qInput);
  const qIsValid = Number.isFinite(qNumericRaw) && qNumericRaw > 0;
  const qError =
    qInput.trim() === ""
      ? null
      : !Number.isFinite(qNumericRaw) || qNumericRaw <= 0
        ? "Расход должен быть больше нуля"
        : qNumericRaw > Q_HERO_MAX
          ? "При расходе свыше 10 000 м³/ч обратитесь к инженеру"
          : null;

  // Mode-aware CTA. Без обещания «60 сек» — это создаёт false expectation
  // против формы с 4 полями. Лаконично и честно.
  const heroCtaText = isCalculating
    ? "Считаем…"
    : mode === "engineer"
      ? "Рассчитать"
      : "Подобрать насос";
  const qLabel = mode === "engineer" ? "Q, м³/ч" : "Расход, м³/ч";

  const handleDownload = async (filename: string) => {
    setDownloadError(null);
    try {
      await downloadEmptyQuestionnaire(filename);
    } catch (e) {
      setDownloadError(
        e instanceof Error
          ? e.message
          : "Не удалось скачать форму. Попробуйте позже.",
      );
    }
  };

  return (
    <section id="hero" className="kns-hero">
      <div className="kns-shell kns-hero-grid">
        <div className="kns-hero-copy">
          <h1>Подбор насоса <span>для КНС</span></h1>
          <p className="kns-hero-intro">
            Укажите расход, чтобы подобрать насос и узнать ориентировочную стоимость комплекта.
          </p>

          <form
            className="kns-quick-form"
            noValidate
            onSubmit={(event) => {
              event.preventDefault();
              if (qIsValid && !qError && !isCalculating) onCalculate(qNumericRaw);
            }}
          >
            <div className="kns-quick-fields">
              <div className="kns-quick-field">
                <label htmlFor="hero-q">{qLabel}</label>
                <input
                  id="hero-q"
                  type="number"
                  inputMode="decimal"
                  value={qInput}
                  onChange={(event) => setQInput(event.target.value)}
                  step="any"
                  min="0"
                  max={Q_HERO_MAX}
                  aria-invalid={qError !== null}
                  aria-describedby={qError ? "hero-q-error" : "hero-q-hint"}
                />
              </div>
              <button className="kns-primary" type="submit" disabled={isCalculating || !qIsValid || !!qError}>
                {heroCtaText}
                <ArrowRight size={18} aria-hidden="true" />
              </button>
            </div>
            {qError ? (
              <p id="hero-q-error" role="alert" className="kns-error">{qError}</p>
            ) : (
              <p id="hero-q-hint" className="kns-form-hint">
                Без регистрации. Предварительный подбор по расходу.
              </p>
            )}
          </form>

          <div className="kns-hero-actions">
            <a href="#calculator"><SlidersHorizontal size={16} aria-hidden="true" /> Все параметры</a>
            <button type="button" onClick={() => handleDownload("Техзадание_КНС.docx")}>
              <FileDown size={16} aria-hidden="true" /> Техзадание
            </button>
            <button type="button" onClick={() => handleDownload("Опросный_лист_КНС.docx")}>
              <FileDown size={16} aria-hidden="true" /> Опросный лист
            </button>
          </div>
          {downloadError && <p role="alert" className="kns-error">{downloadError}</p>}
        </div>

        <aside className="kns-reading" aria-labelledby="reading-title">
          <h2 id="reading-title">Что покажет расчёт</h2>
          <dl>
            <div>
              <dt>Модели насосов</dt>
              <dd>Подходящие варианты по ценовым сегментам.</dd>
            </div>
            <div>
              <dt>Напор и стоимость</dt>
              <dd>Расчётный напор в метрах и ориентировочный диапазон цены комплекта.</dd>
            </div>
            <div>
              <dt>Допущения</dt>
              <dd>Параметры, которые калькулятор подставил вместо пропущенных.</dd>
            </div>
          </dl>
        </aside>
      </div>
    </section>
  );
}
