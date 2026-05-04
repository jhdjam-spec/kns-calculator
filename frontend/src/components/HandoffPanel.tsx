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
      triggerDownload(blob, "Опросный_лист_КНС.pdf");
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
      triggerDownload(blob, "Спецификация_КНС.pdf");
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
          {handoffNeeded ? "Передать инженеру Серво-Юг" : "Можно формировать КП"}
        </h3>
      </header>

      {handoffNeeded ? (
        <>
          <p className="text-sm text-blue-900">
            Условия задачи требуют дополнительного расчёта инженером:
          </p>
          <ul className="text-sm text-blue-900 list-disc pl-5 space-y-1">
            {result.trigger_reasons.map((reason) => (
              <li key={reason}>{triggerReasonLabels[reason] ?? reason}</li>
            ))}
          </ul>
          <p className="text-xs text-blue-800 pt-1">
            Скачайте опросный лист и спецификацию — отправьте инженеру или заказчику для согласования.
          </p>
        </>
      ) : (
        <p className="text-sm text-green-900">
          Можно отправить коммерческое предложение клиенту по выбранному варианту.
          Опросный лист — для уточнения деталей; спецификация — для согласования цены.
        </p>
      )}

      <div className="flex flex-col sm:flex-row flex-wrap gap-2 pt-2">
        <button
          type="button"
          onClick={downloadBom}
          disabled={bomState === "loading"}
          className="rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold px-4 py-2.5 text-sm shadow-sm transition flex-1 sm:flex-initial"
        >
          {bomState === "loading"
            ? "Готовим PDF..."
            : "Сформировать КП (PDF)"}
        </button>

        <button
          type="button"
          onClick={downloadQuestionnaire}
          disabled={qState === "loading"}
          className="rounded-md bg-white border border-blue-600 text-blue-700 hover:bg-blue-50 disabled:opacity-50 font-medium px-4 py-2.5 text-sm transition flex-1 sm:flex-initial"
        >
          {qState === "loading"
            ? "Готовим PDF..."
            : "Опросный лист клиенту"}
        </button>
      </div>

      {errorMsg && (
        <p className="text-xs text-red-700" role="alert">
          Ошибка: {errorMsg}. Убедитесь, что backend запущен на :8000.
        </p>
      )}

      <p className="text-xs text-gray-600 pt-1">
        <strong>Спецификация (КП)</strong> — таблица оборудования с ценами по 3 сегментам.{" "}
        <strong>Опросный лист</strong> — анкета на 10 разделов для согласования с клиентом.
      </p>
    </aside>
  );
}
