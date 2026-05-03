import type { L0Input } from "@/schemas/input";
import { selectionResultSchema, type SelectionResult } from "@/schemas/result";

/**
 * Базовый URL для backend.
 * - В dev режиме next.config.mjs делает rewrite /api/backend/* → http://localhost:8000/*
 * - В production — задаётся через NEXT_PUBLIC_API_BASE
 */
const API_PREFIX = "/api/backend";

export async function selectPumpsQuick(input: L0Input): Promise<SelectionResult> {
  const res = await fetch(`${API_PREFIX}/select/quick`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Backend error ${res.status}: ${text}`);
  }

  const json = await res.json();
  // Валидируем shape — это защита от рассинхрона backend/frontend
  return selectionResultSchema.parse(json);
}

export interface HealthInfo {
  status: string;
  version: string;
  pumps_in_db: number;
  coefficients_loaded: number;
}

export async function healthCheck(): Promise<HealthInfo> {
  const res = await fetch(`${API_PREFIX}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return (await res.json()) as HealthInfo;
}

// ----------- Phase 4 PDF endpoints -----------

export interface QuestionnaireMeta {
  object_name?: string;
  client_company?: string;
  client_contact?: string;
  city?: string;
  kp_number?: string;
}

/** Скачать PDF опросный лист как Blob (для триггера download). */
export async function fetchQuestionnairePdf(
  selection: SelectionResult,
  meta: QuestionnaireMeta = {}
): Promise<Blob> {
  const res = await fetch(`${API_PREFIX}/handoff/questionnaire`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selection, ...meta }),
  });
  if (!res.ok) {
    throw new Error(`Questionnaire PDF failed: ${res.status}`);
  }
  return res.blob();
}

/** Скачать PDF BOM-черновика. */
export async function fetchBomPdf(selection: SelectionResult): Promise<Blob> {
  const res = await fetch(`${API_PREFIX}/handoff/bom`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(selection),
  });
  if (!res.ok) {
    throw new Error(`BOM PDF failed: ${res.status}`);
  }
  return res.blob();
}

/** Триггерит скачивание Blob как файла в браузере. */
export function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
