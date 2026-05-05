"use client";

import { useState, useRef } from "react";
import {
  selectFromFile,
  fetchEmptyQuestionnaireDocx,
  triggerDownload,
  type SelectFromFileResult,
} from "@/lib/api";
import type { SelectionResult } from "@/schemas/result";

export interface QuizUploaderProps {
  onResult: (result: SelectionResult, fromFile: SelectFromFileResult) => void;
}

type UploadState = "idle" | "uploading" | "done" | "error";

const MISSING_LABELS: Record<string, string> = {
  Q_M3H: "Расход Q (м³/ч или л/с)",
  DH_M_OR_H_M: "Напор H или геометрический перепад ΔH",
  WASTEWATER_TYPE: "Тип стоков",
};

export function QuizUploader({ onResult }: QuizUploaderProps) {
  const [state, setState] = useState<UploadState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [parsed, setParsed] = useState<SelectFromFileResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function downloadEmpty() {
    try {
      const blob = await fetchEmptyQuestionnaireDocx();
      triggerDownload(blob, "Опросный_лист_КНС_пустой.docx");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "ошибка скачивания");
    }
  }

  async function handleFile(file: File) {
    setState("uploading");
    setErrorMsg(null);
    setParsed(null);
    try {
      const result = await selectFromFile(file);
      setParsed(result);
      if (result.selection) {
        onResult(result.selection, result);
        setState("done");
      } else {
        setState("error");
        setErrorMsg(
          `Не удалось извлечь обязательные поля: ${result.missing_fields
            .map((f) => MISSING_LABELS[f] ?? f)
            .join(", ")}. Заполните их в форме выше или верните DOCX с заполненными полями.`,
        );
      }
    } catch (e) {
      setState("error");
      setErrorMsg(e instanceof Error ? e.message : "ошибка загрузки");
    }
  }

  function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
  }

  function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFile(file);
    }
  }

  return (
    <section className="rounded-md border border-gray-300 bg-white p-4 space-y-3">
      <header>
        <h3 className="text-base font-semibold text-gray-900">
          Загрузить заполненный опросный лист
        </h3>
        <p className="text-xs text-gray-600 mt-1">
          Если клиент уже прислал DOCX-опросник — загрузите его, и калькулятор
          автоматически распознает параметры и сделает подбор. Если бланка нет —{" "}
          <button
            type="button"
            onClick={downloadEmpty}
            className="text-blue-700 underline hover:text-blue-900"
          >
            скачайте пустой шаблон
          </button>
          .
        </p>
      </header>

      <div
        onClick={() => inputRef.current?.click()}
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        className="rounded-md border-2 border-dashed border-gray-300 hover:border-blue-400 hover:bg-blue-50 cursor-pointer p-6 text-center transition"
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={onChange}
          className="hidden"
        />
        {state === "uploading" ? (
          <p className="text-sm text-gray-700">Распознаём опросник…</p>
        ) : (
          <>
            <p className="text-sm text-gray-700">
              Перетащите DOCX-файл сюда или нажмите для выбора
            </p>
            <p className="text-xs text-gray-500 mt-1">Только формат DOCX</p>
          </>
        )}
      </div>

      {state === "done" && parsed && (
        <div className="rounded-md bg-green-50 border border-green-200 p-3 text-sm">
          <p className="text-green-900 font-medium">
            ✓ Распознано {Object.keys(parsed.extracted_codes).filter((k) => parsed.extracted_codes[k]).length} полей
          </p>
          {parsed.warnings.length > 0 && (
            <ul className="text-xs text-green-800 mt-1 list-disc pl-5 space-y-0.5">
              {parsed.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
          {parsed.metadata.OBJECT_NAME && (
            <p className="text-xs text-green-800 mt-1">
              Объект: <strong>{parsed.metadata.OBJECT_NAME}</strong>
              {parsed.metadata.CITY && `, ${parsed.metadata.CITY}`}
            </p>
          )}
          <p className="text-xs text-green-800 mt-1">
            Подбор сделан — смотрите результаты ниже.
          </p>
        </div>
      )}

      {errorMsg && (
        <div className="rounded-md bg-amber-50 border border-amber-200 p-3 text-sm">
          <p className="text-amber-900">{errorMsg}</p>
        </div>
      )}
    </section>
  );
}
