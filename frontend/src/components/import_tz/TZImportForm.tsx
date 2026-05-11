// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — TZ Import (Phase 33).                                │
// │ Менеджер вставляет ТЗ → /import/parse → pre-filled L0/L1 для wizard.  │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { useRef, useState, type DragEvent } from "react";
import clsx from "clsx";
import {
  Loader2,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  Zap,
  FileText,
  Upload,
} from "lucide-react";

export interface TZParseResponse {
  Q_m3h: number | null;
  dH_m: number | null;
  city: string | null;
  wastewater_type: string | null;
  project_code: string | null;
  project_codes: string[];
  object_type: string | null;
  manufacturer: string | null;
  Ex_required: boolean;
  reliability: string | null;
  liquid_temp_c: number | null;
  extracted_text_chars: number;
  confidence: number;
  fields_found: string[];
  raw_matches: Record<string, unknown>;
  // Phase 33+: архив оригиналов на Я.Диске (best-effort)
  archive_path?: string | null;
  archive_error?: string | null;
  archive_size_bytes?: number;
}

interface TZImportFormProps {
  /** Override fetch (для unit-тестов). По умолчанию — глобальный fetch. */
  fetchImpl?: typeof fetch;
}

const STORAGE_KEY = "inservo:kns:import:tz:draft";

const SAMPLE_PLACEHOLDER = `Например:

Тех.задание на разработку КНС жилого комплекса.
Производительность: Q = 88.6 м³/ч, напор 39 м.
Город: г. Краснодар. Тип стоков: бытовые.
Шифр проекта: 1578-22-НК`;

const WASTEWATER_LABEL: Record<string, string> = {
  domestic: "бытовые",
  industrial: "промышленные",
  drainage: "ливнёвые",
  fire_protection: "пожарные",
  clean_water: "чистая вода",
};

function loadDraft(): string {
  if (typeof window === "undefined") return "";
  try {
    return localStorage.getItem(STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

function saveDraft(text: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, text);
  } catch {
    // ignore (quota / private mode)
  }
}

function buildProjectURL(r: TZParseResponse): string {
  const params = new URLSearchParams();
  params.set("preset", "auto");
  if (r.Q_m3h !== null) params.set("q", String(r.Q_m3h));
  if (r.dH_m !== null) params.set("dh", String(r.dH_m));
  if (r.city) params.set("city", r.city);
  if (r.wastewater_type) params.set("wastewater", r.wastewater_type);
  if (r.project_code) params.set("code", r.project_code);
  if (r.Ex_required) params.set("ex", "1");
  if (r.reliability) params.set("reliability", r.reliability);
  return `/project?${params.toString()}`;
}

function buildQuickSelectURL(r: TZParseResponse): string {
  const params = new URLSearchParams();
  if (r.Q_m3h !== null) params.set("q", String(r.Q_m3h));
  if (r.dH_m !== null) params.set("dh", String(r.dH_m));
  return `/#calculator?${params.toString()}`;
}

export function TZImportForm({ fetchImpl }: TZImportFormProps = {}) {
  const [text, setText] = useState<string>(() => loadDraft());
  const [result, setResult] = useState<TZParseResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Имя файла, если ТЗ пришло из file-upload (для архива на Я.Диск)
  const [originalFilename, setOriginalFilename] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const isEmpty = text.trim() === "";

  const handleParse = async () => {
    if (isEmpty) {
      setError("Вставьте текст ТЗ");
      return;
    }
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE || "/api/backend";
      const fetchFn = fetchImpl ?? fetch;
      const body: {
        text: string;
        format: "plain";
        original_filename?: string;
      } = { text, format: "plain" };
      if (originalFilename) {
        body.original_filename = originalFilename;
      }
      const response = await fetchFn(`${apiBase}/import/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const respBody = await response.text().catch(() => response.statusText);
        throw new Error(`HTTP ${response.status}: ${respBody}`);
      }
      const data = (await response.json()) as TZParseResponse;
      setResult(data);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setText("");
    setResult(null);
    setError(null);
    setOriginalFilename(null);
    saveDraft("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleFileSelected = async (file: File) => {
    setError(null);
    setOriginalFilename(file.name);
    // .txt / .md / .csv — читаем как текст; DOCX/PDF — оставляем placeholder
    // (вставка текста через textarea обязательна, бинарные форматы
    // распарсятся когда будет /import/parse-file endpoint).
    const ext = (file.name.split(".").pop() || "").toLowerCase();
    const isText = ["txt", "md", "csv", "log", ""].includes(ext);
    if (isText) {
      try {
        const content = await file.text();
        setText(content);
        saveDraft(content);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setError(`Не удалось прочитать файл: ${msg}`);
      }
    } else {
      setError(
        `Формат .${ext} пока не парсится. Скопируйте текст ТЗ вручную — ` +
          `имя файла (${file.name}) сохранится в архиве.`,
      );
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) void handleFileSelected(file);
  };

  const handleDragOver = (e: DragEvent<HTMLTextAreaElement>) => {
    e.preventDefault();
    if (!isDragging) setIsDragging(true);
  };
  const handleDragLeave = () => {
    setIsDragging(false);
  };
  const handleDrop = (e: DragEvent<HTMLTextAreaElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void handleFileSelected(file);
  };

  return (
    <div className="grid lg:grid-cols-2 gap-6">
      {/* Левая колонка — ввод ТЗ */}
      <section
        aria-labelledby="tz-input-heading"
        className="bg-white border border-ink-200 rounded-lg p-5 md:p-6 shadow-premium-sm"
      >
        <div className="flex items-center gap-2 mb-4">
          <FileText size={18} strokeWidth={1.75} className="text-brand-600" />
          <h2
            id="tz-input-heading"
            className="text-base font-semibold text-ink-900"
          >
            Вставьте ТЗ или опросный лист
          </h2>
        </div>

        <div className="flex items-center justify-between mb-1.5">
          <label htmlFor="tz-text" className="block text-sm text-ink-700">
            Текст технического задания
          </label>
          <label
            data-testid="tz-file-upload-label"
            className="inline-flex items-center gap-1.5 text-xs text-brand-600 hover:text-brand-700 cursor-pointer"
          >
            <Upload size={13} strokeWidth={1.75} />
            <span>Загрузить файл</span>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.csv,.log,.docx,.pdf"
              className="hidden"
              onChange={handleFileChange}
              data-testid="tz-file-input"
            />
          </label>
        </div>
        <textarea
          id="tz-text"
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            saveDraft(e.target.value);
          }}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          rows={14}
          placeholder={SAMPLE_PLACEHOLDER}
          className={clsx(
            "w-full bg-ink-50 border text-ink-900 rounded-md px-3 py-2 placeholder:text-ink-500 focus:outline-none font-sans text-sm leading-relaxed transition-colors",
            isDragging
              ? "border-brand-500 bg-brand-50"
              : "border-ink-200 focus:border-brand-500",
          )}
          data-testid="tz-textarea"
        />

        <div className="mt-2 text-xs text-ink-600 flex items-center justify-between">
          <span>
            {text.length} символов
            {originalFilename && (
              <span
                className="ml-2 text-brand-700"
                data-testid="tz-original-filename"
              >
                · {originalFilename}
              </span>
            )}
          </span>
          {text.length > 8000 && (
            <span className="text-amber-700">Очень длинный текст — парсер обрабатывает first-match</span>
          )}
        </div>

        <div className="flex items-center gap-3 mt-5">
          <button
            type="button"
            onClick={handleParse}
            disabled={isLoading || isEmpty}
            data-testid="tz-parse-btn"
            className={clsx(
              "inline-flex items-center justify-center gap-2 h-11 px-5 rounded-md text-sm font-medium transition-colors",
              "bg-brand-600 hover:bg-brand-700 text-white",
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
            className="inline-flex items-center justify-center h-11 px-4 rounded-md text-sm text-ink-700 hover:text-ink-900 hover:bg-ink-100 transition-colors"
          >
            Очистить
          </button>
        </div>

        {error && (
          <div
            role="alert"
            className="mt-4 flex items-start gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3"
          >
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
      </section>

      {/* Правая колонка — результат + CTA */}
      <section
        aria-labelledby="tz-result-heading"
        aria-live="polite"
        className="bg-white border border-ink-200 rounded-lg p-5 md:p-6 shadow-premium-sm"
      >
        <h2
          id="tz-result-heading"
          className="text-base font-semibold text-ink-900 mb-4"
        >
          Распознанные параметры
        </h2>

        {!result && !isLoading && (
          <div className="text-sm text-ink-600 space-y-3">
            <p>
              Вставьте ТЗ слева и нажмите «Распознать». Калькулятор извлечёт
              расход, напор, город, тип стоков и шифр — данные подставятся в
              мастер проекта автоматически.
            </p>
            <ul className="space-y-1.5 text-xs text-ink-600 list-disc list-inside pl-1">
              <li>Распознаёт Q в м³/ч, л/с, м³/сут</li>
              <li>Распознаёт H («напор», «H=…», «высота подъёма»)</li>
              <li>76 городов из climate_cities_2026.json</li>
              <li>Шифры формата 1578-22-НК, ЖК-Крокус-2024, 2799289</li>
            </ul>
          </div>
        )}

        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-ink-600">
            <Loader2 size={16} className="animate-spin" />
            <span>Анализирую текст…</span>
          </div>
        )}

        {result && (
          <div className="space-y-4" data-testid="tz-result">
            {/* Confidence bar */}
            <div>
              <div className="flex items-center justify-between text-xs uppercase tracking-wider text-ink-600 mb-1.5">
                <span>Уверенность</span>
                <span data-testid="tz-confidence">
                  {Math.round(result.confidence * 100)}% ·{" "}
                  {result.fields_found.length}/4 ключевых полей
                </span>
              </div>
              <div className="h-2 bg-ink-100 rounded-full overflow-hidden">
                <div
                  className={clsx(
                    "h-full transition-all duration-500",
                    result.confidence >= 0.75
                      ? "bg-emerald-500"
                      : result.confidence >= 0.5
                        ? "bg-amber-500"
                        : "bg-red-500",
                  )}
                  style={{ width: `${Math.round(result.confidence * 100)}%` }}
                />
              </div>
            </div>

            {/* Extracted fields */}
            <ul className="space-y-2 text-sm">
              <ExtractedField
                ok={result.Q_m3h !== null}
                label="Расход Q"
                value={result.Q_m3h !== null ? `${result.Q_m3h} м³/ч` : null}
                testId="tz-q"
              />
              <ExtractedField
                ok={result.dH_m !== null}
                label="Напор H"
                value={result.dH_m !== null ? `${result.dH_m} м` : null}
                testId="tz-h"
              />
              <ExtractedField
                ok={result.city !== null}
                label="Город"
                value={result.city}
                testId="tz-city"
              />
              <ExtractedField
                ok={result.wastewater_type !== null}
                label="Тип стоков"
                value={
                  result.wastewater_type
                    ? (WASTEWATER_LABEL[result.wastewater_type] ??
                      result.wastewater_type)
                    : null
                }
                testId="tz-wastewater"
              />
              {result.object_type && (
                <ExtractedField
                  ok
                  label="Объект"
                  value={result.object_type}
                  testId="tz-object"
                />
              )}
              {result.project_code && (
                <ExtractedField
                  ok
                  label="Шифр проекта"
                  value={result.project_code}
                  testId="tz-code"
                />
              )}
              {result.manufacturer && (
                <ExtractedField
                  ok
                  label="Производитель упомянут"
                  value={result.manufacturer}
                  testId="tz-manufacturer"
                />
              )}
              {result.Ex_required && (
                <ExtractedField
                  ok
                  label="Взрывозащита"
                  value="требуется (Ex / ATEX)"
                  testId="tz-ex"
                />
              )}
              {result.reliability && (
                <ExtractedField
                  ok
                  label="Категория надёжности"
                  value={result.reliability}
                  testId="tz-reliability"
                />
              )}
              {result.liquid_temp_c !== null && (
                <ExtractedField
                  ok
                  label="t° жидкости"
                  value={`${result.liquid_temp_c} °C`}
                  testId="tz-liquid-temp"
                />
              )}
            </ul>

            {/* CTA blocks */}
            <div className="pt-4 border-t border-ink-200 space-y-2.5">
              <a
                href={buildProjectURL(result)}
                data-testid="tz-cta-project"
                className="group inline-flex w-full items-center justify-between gap-2 px-4 h-11 rounded-md bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium transition-colors"
              >
                <span className="inline-flex items-center gap-2">
                  <ArrowRight size={16} strokeWidth={2} />
                  Создать полный проект
                </span>
                <span className="text-xs opacity-75 font-mono">
                  /project
                </span>
              </a>
              <a
                href={buildQuickSelectURL(result)}
                data-testid="tz-cta-quick"
                className="group inline-flex w-full items-center justify-between gap-2 px-4 h-11 rounded-md border border-ink-200 bg-white hover:bg-ink-50 text-ink-900 text-sm font-medium transition-colors"
              >
                <span className="inline-flex items-center gap-2">
                  <Zap size={16} strokeWidth={1.75} className="text-brand-600" />
                  Быстрый подбор
                </span>
                <span className="text-xs text-ink-600 font-mono">
                  Q={result.Q_m3h ?? "—"}
                </span>
              </a>
            </div>

            {/* Project codes list */}
            {result.project_codes.length > 1 && (
              <div className="pt-3 border-t border-ink-200">
                <div className="text-xs uppercase tracking-wider text-ink-600 mb-1.5">
                  Все найденные шифры
                </div>
                <ul className="flex flex-wrap gap-2">
                  {result.project_codes.map((c) => (
                    <li
                      key={c}
                      className="inline-flex items-center px-2.5 h-7 rounded-md bg-brand-50 border border-brand-200 text-brand-700 text-xs font-mono"
                    >
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* NB: archive_path / archive_error / s3_archive / dataset_enrichment
                в response ВСЕГДА скрыты от пользователя. Это служебная функция
                Серво-Юг (dataset enrichment + audit) — пользователю показывать
                нельзя по требованию заказчика. Backend сохраняет в фоне,
                независимо от того видит ли это UI. */}
          </div>
        )}
      </section>
    </div>
  );
}

function ExtractedField({
  ok,
  label,
  value,
  testId,
}: {
  ok: boolean;
  label: string;
  value: string | null;
  testId?: string;
}) {
  return (
    <li
      data-testid={testId}
      className="flex items-start gap-2.5 py-1.5 border-b border-ink-100 last:border-b-0"
    >
      {ok ? (
        <CheckCircle2
          size={16}
          strokeWidth={1.75}
          className="shrink-0 mt-0.5 text-emerald-600"
        />
      ) : (
        <AlertCircle
          size={16}
          strokeWidth={1.75}
          className="shrink-0 mt-0.5 text-ink-400"
        />
      )}
      <div className="flex-1 flex items-baseline justify-between gap-3">
        <span className="text-xs uppercase tracking-wider text-ink-600">
          {label}
        </span>
        <span
          className={clsx(
            "text-sm font-medium",
            ok ? "text-ink-900" : "text-ink-500",
          )}
        >
          {value ?? "— не извлечено"}
        </span>
      </div>
    </li>
  );
}
