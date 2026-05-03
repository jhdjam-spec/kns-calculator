"use client";

import type { SelectionResult } from "@/schemas/result";
import { triggerReasonLabels } from "@/schemas/result";

export interface HandoffPanelProps {
  result: SelectionResult;
}

export function HandoffPanel({ result }: HandoffPanelProps) {
  if (!result.engineer_handoff_required && result.trigger_reasons.length === 0) {
    return (
      <aside className="rounded-md bg-green-50 border border-green-200 p-4">
        <p className="text-sm text-green-900">
          ✅ Типовой случай. Можно отправить КП клиенту по выбранному варианту,
          инженер не требуется.
        </p>
      </aside>
    );
  }

  return (
    <aside className="rounded-md bg-blue-50 border border-blue-200 p-4 space-y-3">
      <header className="flex items-baseline justify-between gap-3 flex-wrap">
        <h3 className="text-lg font-semibold text-blue-900">
          Требуется инженерный расчёт
        </h3>
      </header>

      <p className="text-sm text-blue-900">
        Условия задачи требуют дополнительной проработки специалистом:
      </p>

      <ul className="text-sm text-blue-900 list-disc pl-5 space-y-1">
        {result.trigger_reasons.map((reason) => (
          <li key={reason}>{triggerReasonLabels[reason] ?? reason}</li>
        ))}
      </ul>

      <button
        type="button"
        className="rounded-md bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 text-sm"
        onClick={() => alert("Hand-off API будет реализован в Phase 4 (PDF + email инженеру)")}
      >
        Передать инженеру (Phase 4)
      </button>
    </aside>
  );
}
