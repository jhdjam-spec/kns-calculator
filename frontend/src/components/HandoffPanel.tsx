"use client";

import { useState } from "react";
import type { SelectionResult } from "@/schemas/result";
import { triggerReasonLabels } from "@/schemas/result";
import { fetchQuestionnairePdf, fetchBomPdf, triggerDownload } from "@/lib/api";

export interface HandoffPanelProps {
  result: SelectionResult;
}

type DownloadState = "idle" | "loading" | "error";

export function HandoffPanel({ result }: HandoffPanelProps) {
  const [qState, setQState] = useState<DownloadState>("idle");
  const [bomState, setBomState] = useState<DownloadState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function downloadQuestionnaire() {
    setQState("loading");
    setErrorMsg(null);
    try {
      const blob = await fetchQuestionnairePdf(result);
      triggerDownload(blob, "kns_questionnaire.pdf");
      setQState("idle");
    } catch (e) {
      setQState("error");
      setErrorMsg(e instanceof Error ? e.message : "ошибка скачивания");
    }
  }

  async function downloadBom() {
    setBomState("loading");
    setErrorMsg(null);
    try {
      const blob = await fetchBomPdf(result);
      triggerDownload(blob, "kns_bom_draft.pdf");
      setBomState("idle");
    } catch (e) {
      setBomState("error");
      setErrorMsg(e instanceof Error ? e.message : "ошибка скачивания");
    }
  }

  const handoffNeeded = result.engineer_handoff_required || result.trigger_reasons.length > 0;

  return (
    <aside
      className={`rounded-md border p-4 space-y-3 ${
        handoffNeeded
          ? "bg-blue-50 border-blue-200"
          : "bg-green-50 border-green-200"
      }`}
    >
      <header>
        <h3 className={`text-lg font-semibold ${handoffNeeded ? "text-blue-900" : "text-green-900"}`}>
          {handoffNeeded ? "Требуется инженерный расчёт" : "Типовой случай"}
        </h3>
      </header>

      {handoffNeeded ? (
        <>
          <p className="text-sm text-blue-900">
            Условия задачи требуют дополнительной проработки специалистом:
          </p>
          <ul className="text-sm text-blue-900 list-disc pl-5 space-y-1">
            {result.trigger_reasons.map((reason) => (
              <li key={reason}>{triggerReasonLabels[reason] ?? reason}</li>
            ))}
          </ul>
        </>
      ) : (
        <p className="text-sm text-green-900">
          ✅ Можно отправить КП клиенту по выбранному варианту. Опросник пригодится
          для уточнений; BOM-черновик — для согласования цены.
        </p>
      )}

      <div className="flex flex-wrap gap-2 pt-2">
        <button
          type="button"
          onClick={downloadQuestionnaire}
          disabled={qState === "loading"}
          className="rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium px-4 py-2 text-sm"
        >
          {qState === "loading" ? "Готовим PDF..." : "📄 Опросный лист (PDF)"}
        </button>

        <button
          type="button"
          onClick={downloadBom}
          disabled={bomState === "loading"}
          className="rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium px-4 py-2 text-sm"
        >
          {bomState === "loading" ? "Готовим PDF..." : "📋 BOM-черновик (PDF)"}
        </button>
      </div>

      {errorMsg && (
        <p className="text-xs text-red-700" role="alert">
          Ошибка: {errorMsg}. Убедитесь, что backend запущен на :8000.
        </p>
      )}

      <p className="text-xs text-gray-600 pt-1">
        Опросник — структурированная анкета 10 секций для уточнения у клиента.
        BOM-черновик — таблица 8+ позиций обвязки × 3 ценовых сегмента с
        ориентировочными ценами 2026.
      </p>
    </aside>
  );
}
