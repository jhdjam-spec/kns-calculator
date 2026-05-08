"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  projectApi,
  encyclopediaApi,
  type ProjectInput,
  type ProjectResult,
} from "@/lib/api-extended";

/** Список 13 пресетов проекта (загружается раз). */
export function useProjectPresets() {
  return useQuery({
    queryKey: ["project-presets"],
    queryFn: () => projectApi.listPresets(),
    staleTime: 1000 * 60 * 60,    // 1 час — пресеты редко меняются
  });
}

/** Расчёт проекта со всеми подсистемами. */
export function useProjectCalculate() {
  return useMutation<ProjectResult, Error, ProjectInput>({
    mutationFn: (input: ProjectInput) => projectApi.calculate(input),
    retry: 1,
  });
}

/** Список тем энциклопедии для /teach. */
export function useEncyclopediaTopics() {
  return useQuery({
    queryKey: ["encyclopedia-topics"],
    queryFn: () => encyclopediaApi.listTopics(),
    staleTime: 1000 * 60 * 60,
  });
}

/** Полная статья по теме. */
export function useEncyclopediaTopic(topicKey: string | null) {
  return useQuery({
    queryKey: ["encyclopedia-topic", topicKey],
    queryFn: () => encyclopediaApi.getTopic(topicKey!),
    enabled: !!topicKey,
  });
}

/** Список интерактивных примеров. */
export function useEncyclopediaExamples() {
  return useQuery({
    queryKey: ["encyclopedia-examples"],
    queryFn: () => encyclopediaApi.listExamples(),
    staleTime: 1000 * 60 * 60,
  });
}
