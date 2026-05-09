import type { L0Input, SelectionRequest } from "@/schemas/input";
import { selectionResultSchema, type SelectionResult } from "@/schemas/result";

/**
 * Базовый URL для backend.
 * - В dev режиме next.config.mjs делает rewrite /api/backend/* → http://localhost:8000/*
 * - В production — задаётся через NEXT_PUBLIC_API_BASE
 */
// Same-origin path: `/api/backend/*` → backend.
// - На Vercel: vercel.json rewrites → YC API Gateway.
// - В dev: next.config.mjs переписывает /api/backend/* → http://localhost:8000/*.
// - На YC Object Storage static (BUILD_TARGET=yc-static): нужен прямой URL,
//   задаётся через NEXT_PUBLIC_API_BASE на build time.
const API_PREFIX =
  process.env.NEXT_PUBLIC_API_BASE
    ? `${process.env.NEXT_PUBLIC_API_BASE}`
    : "/api/backend";

/** /select/quick — только L0, без L1. Backward-compat. */
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
  return selectionResultSchema.parse(json);
}

/** /select — полный запрос с L0 + опциональным L1 (corpus_material и др.). */
export async function selectPumps(req: SelectionRequest): Promise<SelectionResult> {
  // Если L1 пустой/отсутствует — используем quick endpoint (он быстрее и без обёртки L0/L1)
  if (!req.L1 || Object.keys(req.L1).length === 0) {
    return selectPumpsQuick(req.L0);
  }

  const res = await fetch(`${API_PREFIX}/select`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Backend error ${res.status}: ${text}`);
  }

  const json = await res.json();
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

// ----------- Phase 12: DOCX опросник + парсинг -----------

/**
 * Скачать DOCX опросный лист с предзаполнением из текущего подбора.
 * В отличие от PDF — DOCX можно редактировать в Word, а потом загрузить
 * обратно через /select/from-file (парсер извлечёт значения).
 */
export async function fetchQuestionnaireDocx(
  selection: SelectionResult,
  meta: QuestionnaireMeta = {}
): Promise<Blob> {
  const res = await fetch(`${API_PREFIX}/handoff/questionnaire-docx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selection, ...meta }),
  });
  if (!res.ok) {
    throw new Error(`Questionnaire DOCX failed: ${res.status}`);
  }
  return res.blob();
}

/** Скачать пустой DOCX опросник (для клиентов, заполняющих с нуля). */
export async function fetchEmptyQuestionnaireDocx(): Promise<Blob> {
  const res = await fetch(`${API_PREFIX}/handoff/empty-questionnaire-docx`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Empty questionnaire DOCX failed: ${res.status}`);
  }
  return res.blob();
}

export interface SelectFromFileResult {
  extracted_codes: Record<string, string>;
  L0: L0Input | null;
  L1_provided: boolean;
  metadata: Record<string, string>;
  missing_fields: string[];
  warnings: string[];
  selection: SelectionResult | null;
}

/**
 * Загрузить заполненный клиентом DOCX и получить распарсенный L0 + результат подбора.
 *
 * Если Q не извлечён — selection=null, missing_fields=["Q_M3H", ...] —
 * UI должен показать форму для ручного дозаполнения.
 */
export async function selectFromFile(file: File): Promise<SelectFromFileResult> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_PREFIX}/select/from-file`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Select from file failed: ${res.status}: ${text}`);
  }
  return (await res.json()) as SelectFromFileResult;
}
