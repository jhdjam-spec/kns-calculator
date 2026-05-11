// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — CRM-light классификатор входящих писем (P5 mail).    │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { useState } from "react";
import clsx from "clsx";
import { ShieldCheck, ShieldAlert, Loader2, AlertCircle } from "lucide-react";

export interface ClassifyResponse {
  type: string | null;
  object: string | null;
  manufacturer: string | null;
  project_codes: string[];
  is_trusted_sender: boolean;
}

interface ClassifyFormProps {
  /** Override fetch (для unit-тестов). По умолчанию — глобальный fetch. */
  fetchImpl?: typeof fetch;
}

const STORAGE_KEY = "inservo:kns:crm:classify:draft";

interface DraftState {
  subject: string;
  body: string;
  fromEmail: string;
}

function loadDraft(): DraftState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as DraftState;
  } catch {
    return null;
  }
}

function saveDraft(state: DraftState): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // ignore
  }
}

export function ClassifyForm({ fetchImpl }: ClassifyFormProps = {}) {
  const initial = (typeof window !== "undefined" && loadDraft()) || {
    subject: "",
    body: "",
    fromEmail: "",
  };
  const [subject, setSubject] = useState(initial.subject);
  const [body, setBody] = useState(initial.body);
  const [fromEmail, setFromEmail] = useState(initial.fromEmail);
  const [result, setResult] = useState<ClassifyResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const persist = (patch: Partial<DraftState>) => {
    const next: DraftState = {
      subject: patch.subject ?? subject,
      body: patch.body ?? body,
      fromEmail: patch.fromEmail ?? fromEmail,
    };
    saveDraft(next);
  };

  const isEmpty =
    subject.trim() === "" && body.trim() === "" && fromEmail.trim() === "";

  const handleClassify = async () => {
    if (isEmpty) {
      setError("Заполните хотя бы одно поле");
      return;
    }
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE || "/api/backend";
      const fetchFn = fetchImpl ?? fetch;
      const response = await fetchFn(`${apiBase}/etl/classify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject,
          body,
          from_email: fromEmail,
        }),
      });
      if (!response.ok) {
        const text = await response.text().catch(() => response.statusText);
        throw new Error(`HTTP ${response.status}: ${text}`);
      }
      const data = (await response.json()) as ClassifyResponse;
      setResult(data);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setSubject("");
    setBody("");
    setFromEmail("");
    setResult(null);
    setError(null);
    saveDraft({ subject: "", body: "", fromEmail: "" });
  };

  return (
    <div className="grid lg:grid-cols-2 gap-6">
      {/* Левая колонка — форма */}
      <section
        aria-labelledby="classify-form-heading"
        className="bg-white border border-ink-200 dark:bg-ink-900/40 dark:border-white/10 rounded-lg p-5 md:p-6 shadow-premium-sm"
      >
        <h2
          id="classify-form-heading"
          className="text-base font-semibold text-ink-900 dark:text-ink-50 mb-4"
        >
          Входящее письмо
        </h2>

        <label
          htmlFor="classify-subject"
          className="block text-sm text-ink-700 dark:text-ink-300 mb-1"
        >
          Тема письма
        </label>
        <input
          id="classify-subject"
          type="text"
          value={subject}
          onChange={(e) => {
            setSubject(e.target.value);
            persist({ subject: e.target.value });
          }}
          placeholder="Например: ОЛ на КНС-2 для жилого комплекса"
          className="w-full bg-ink-50 border border-ink-200 text-ink-900 dark:bg-ink-950 dark:border-white/10 dark:text-ink-50 rounded-md px-3 h-11 placeholder:text-ink-500 focus:border-brand-500 dark:focus:border-accent-500/60 focus:outline-none"
          autoComplete="off"
        />

        <label
          htmlFor="classify-body"
          className="block text-sm text-ink-700 dark:text-ink-300 mt-4 mb-1"
        >
          Тело письма
        </label>
        <textarea
          id="classify-body"
          value={body}
          onChange={(e) => {
            setBody(e.target.value);
            persist({ body: e.target.value });
          }}
          rows={8}
          placeholder="Прошу подобрать оборудование по шифру 2799289…"
          className="w-full bg-ink-50 border border-ink-200 text-ink-900 dark:bg-ink-950 dark:border-white/10 dark:text-ink-50 rounded-md px-3 py-2 placeholder:text-ink-500 focus:border-brand-500 dark:focus:border-accent-500/60 focus:outline-none font-sans text-sm"
        />

        <label
          htmlFor="classify-email"
          className="block text-sm text-ink-700 dark:text-ink-300 mt-4 mb-1"
        >
          Email отправителя
        </label>
        <input
          id="classify-email"
          type="text"
          value={fromEmail}
          onChange={(e) => {
            setFromEmail(e.target.value);
            persist({ fromEmail: e.target.value });
          }}
          placeholder="user@example.com или ООО Ромашка <info@romashka.ru>"
          className="w-full bg-ink-50 border border-ink-200 text-ink-900 dark:bg-ink-950 dark:border-white/10 dark:text-ink-50 rounded-md px-3 h-11 placeholder:text-ink-500 focus:border-brand-500 dark:focus:border-accent-500/60 focus:outline-none font-mono text-sm"
          autoComplete="off"
          inputMode="email"
        />

        <div className="flex items-center gap-3 mt-5">
          <button
            type="button"
            onClick={handleClassify}
            disabled={isLoading || isEmpty}
            className={clsx(
              "inline-flex items-center justify-center gap-2 h-11 px-5 rounded-md text-sm font-medium transition-colors",
              "bg-brand-600 hover:bg-brand-700 text-white dark:bg-accent-500 dark:text-ink-950 dark:hover:bg-accent-400",
              "disabled:opacity-50 disabled:cursor-not-allowed",
            )}
          >
            {isLoading && <Loader2 size={16} className="animate-spin" />}
            {isLoading ? "Распознаю…" : "Распознать"}
          </button>
          <button
            type="button"
            onClick={handleClear}
            disabled={isLoading}
            className="inline-flex items-center justify-center h-11 px-4 rounded-md text-sm text-ink-700 dark:text-ink-300 hover:text-ink-900 dark:hover:text-ink-50 hover:bg-ink-100 dark:hover:bg-white/5 transition-colors"
          >
            Очистить
          </button>
        </div>

        {error && (
          <div
            role="alert"
            className="mt-4 flex items-start gap-2 text-sm text-red-700 dark:text-red-400 bg-red-50 border border-red-200 dark:bg-red-500/10 dark:border-red-500/30 rounded-md p-3"
          >
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
      </section>

      {/* Правая колонка — результат */}
      <section
        aria-labelledby="classify-result-heading"
        aria-live="polite"
        className="bg-white border border-ink-200 dark:bg-ink-900/40 dark:border-white/10 rounded-lg p-5 md:p-6 shadow-premium-sm"
      >
        <h2
          id="classify-result-heading"
          className="text-base font-semibold text-ink-900 dark:text-ink-50 mb-4"
        >
          Распознано
        </h2>

        {!result && !isLoading && (
          <p className="text-sm text-ink-600 dark:text-ink-500">
            Заполните форму слева и нажмите «Распознать». Калькулятор
            выделит тип запроса (ОЛ/КП/ТЗ), объект (КНС/ЛОС/ВНС),
            производителя и шифры проектов.
          </p>
        )}

        {result && (
          <div className="space-y-4" data-testid="classify-result">
            <ResultField
              label="Тип запроса"
              value={result.type}
              testId="result-type"
            />
            <ResultField
              label="Объект"
              value={result.object}
              testId="result-object"
            />
            <ResultField
              label="Производитель"
              value={result.manufacturer}
              testId="result-manufacturer"
            />

            <div>
              <div className="text-xs uppercase tracking-wider text-ink-600 dark:text-ink-500 mb-1.5">
                Шифры проектов
              </div>
              {result.project_codes.length === 0 ? (
                <span className="text-sm text-ink-600 dark:text-ink-500">— не найдены</span>
              ) : (
                <ul
                  className="flex flex-wrap gap-2"
                  data-testid="project-codes"
                >
                  {result.project_codes.map((code) => (
                    <li
                      key={code}
                      className="inline-flex items-center px-2.5 h-7 rounded-md bg-brand-50 border border-brand-200 text-brand-700 dark:bg-accent-500/15 dark:border-accent-500/40 dark:text-accent-500 text-xs font-mono"
                    >
                      {code}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="pt-3 border-t border-ink-200 dark:border-white/10">
              {result.is_trusted_sender ? (
                <div
                  className="inline-flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-400"
                  data-testid="trusted-indicator"
                >
                  <ShieldCheck size={16} strokeWidth={1.75} />
                  <span>Доверенный отправитель</span>
                </div>
              ) : (
                <div
                  className="inline-flex items-center gap-2 text-sm text-amber-700 dark:text-amber-400"
                  data-testid="untrusted-indicator"
                >
                  <ShieldAlert size={16} strokeWidth={1.75} />
                  <span>Незнакомый домен — проверить вручную</span>
                </div>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function ResultField({
  label,
  value,
  testId,
}: {
  label: string;
  value: string | null;
  testId?: string;
}) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-ink-600 dark:text-ink-500 mb-1">
        {label}
      </div>
      {value ? (
        <span
          data-testid={testId}
          className="inline-flex items-center px-2.5 h-7 rounded-md bg-ink-100 border border-ink-200 text-ink-900 dark:bg-ink-50/5 dark:border-white/10 dark:text-ink-50 text-sm font-medium"
        >
          {value}
        </span>
      ) : (
        <span
          data-testid={testId}
          className="text-sm text-ink-600 dark:text-ink-500"
        >
          — не определено
        </span>
      )}
    </div>
  );
}
