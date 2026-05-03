"use client";

import { useMutation } from "@tanstack/react-query";
import type { L0Input } from "@/schemas/input";
import type { SelectionResult } from "@/schemas/result";
import { selectPumpsQuick } from "@/lib/api";

/**
 * Hook для вызова подбора насосов.
 * Используется как mutation (а не query) потому что:
 * - запрос инициируется явно по submit формы
 * - результат — побочный эффект, не «состояние URL»
 */
export function usePumpSelection() {
  return useMutation<SelectionResult, Error, L0Input>({
    mutationFn: (input: L0Input) => selectPumpsQuick(input),
    retry: 1,
  });
}
