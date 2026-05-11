"use client";

import { useState } from "react";
import { useProjectPresets, useProjectCalculate } from "@/hooks/useProject";
import type { ProjectInput, ProjectResult } from "@/lib/api-extended";
import { ProjectStepPreset } from "./ProjectStepPreset";
import { ProjectStepParams } from "./ProjectStepParams";
import { ProjectStepSubsystems } from "./ProjectStepSubsystems";
import { ProjectStepResults } from "./ProjectStepResults";

type WizardStep = "preset" | "params" | "subsystems" | "results";

const STEPS: { key: WizardStep; title: string; description: string }[] = [
  { key: "preset", title: "Тип объекта", description: "Что вы проектируете" },
  { key: "params", title: "Параметры", description: "Локация, население, объём" },
  { key: "subsystems", title: "Подсистемы", description: "Что нужно рассчитать" },
  { key: "results", title: "Результат", description: "Сводка по проекту" },
];

export function ProjectWizard() {
  const [step, setStep] = useState<WizardStep>("preset");
  const [data, setData] = useState<Partial<ProjectInput>>({
    project_name: "Новый проект",
    region_city: "Краснодар",
    population: 4,
    floors: 1,
    volume_m3: 500,
    area_m2: 200,
    has_groundwater: false,
    soil_type: "clay_loam",
    is_atex_zone: false,
  });

  const presets = useProjectPresets();
  const calculate = useProjectCalculate();

  const currentStepIdx = STEPS.findIndex((s) => s.key === step);

  const goNext = () => {
    if (step === "preset") setStep("params");
    else if (step === "params") setStep("subsystems");
    else if (step === "subsystems") {
      // Запустить расчёт
      if (data.preset && data.project_name && data.region_city) {
        calculate.mutate(data as ProjectInput, {
          onSuccess: () => setStep("results"),
        });
      }
    }
  };

  const goBack = () => {
    if (step === "params") setStep("preset");
    else if (step === "subsystems") setStep("params");
    else if (step === "results") setStep("subsystems");
  };

  return (
    <div className="max-w-5xl mx-auto">
      {/* Шаги */}
      <div className="flex items-center justify-between mb-8">
        {STEPS.map((s, idx) => (
          <div
            key={s.key}
            className={`flex-1 ${idx < STEPS.length - 1 ? "border-r border-ink-200 dark:border-ink-800" : ""}`}
          >
            <div className="px-2 md:px-4">
              <div
                className={`text-xs font-mono uppercase tracking-wider ${
                  idx === currentStepIdx
                    ? "text-brand-700 dark:text-accent-500"
                    : idx < currentStepIdx
                    ? "text-ink-700 dark:text-ink-300"
                    : "text-ink-400 dark:text-ink-600"
                }`}
              >
                {idx + 1}. {s.title}
              </div>
              <div className="text-sm text-ink-600 dark:text-ink-500 mt-1">{s.description}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Контент шага */}
      <div className="bg-white dark:bg-ink-900 border border-ink-200 dark:border-ink-800 rounded-lg p-6 md:p-8 min-h-[400px] shadow-premium-sm">
        {step === "preset" && (
          <ProjectStepPreset
            data={data}
            setData={setData}
            presets={presets.data?.presets || []}
            isLoading={presets.isLoading}
            onNext={goNext}
          />
        )}
        {step === "params" && (
          <ProjectStepParams data={data} setData={setData} onNext={goNext} onBack={goBack} />
        )}
        {step === "subsystems" && (
          <ProjectStepSubsystems
            data={data}
            setData={setData}
            onCalculate={goNext}
            onBack={goBack}
            isCalculating={calculate.isPending}
            error={calculate.error?.message}
          />
        )}
        {step === "results" && calculate.data && (
          <ProjectStepResults
            result={calculate.data}
            onBack={goBack}
            onRestart={() => {
              calculate.reset();
              setStep("preset");
            }}
          />
        )}
      </div>
    </div>
  );
}
