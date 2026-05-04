"use client";

import { useMutation } from "@tanstack/react-query";
import type { SelectionRequest } from "@/schemas/input";
import type { SelectionResult } from "@/schemas/result";
import { selectPumps } from "@/lib/api";

/**
 * Hook для вызова подбора насосов.
 * Используется как mutation (а не query) потому что:
 * - запрос инициируется явно по submit формы
 * - результат — побочный эффект, не «состояние URL»
 *
 * Внутри `selectPumps` сам выбирает endpoint:
 * - если L1 пустой → /select/quick (только L0)
 * - если L1 задан → /select (полный запрос)
 */
export function usePumpSelection() {
  return useMutation<SelectionResult, Error, SelectionRequest>({
    mutationFn: (req: SelectionRequest) => selectPumps(req),
    retry: 1,
  });
}
