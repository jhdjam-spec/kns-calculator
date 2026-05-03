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
