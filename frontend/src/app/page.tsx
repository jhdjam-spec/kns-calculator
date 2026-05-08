"use client";

import { useEffect, useState } from "react";
import { SiteNav } from "@/components/premium/SiteNav";
import { Hero } from "@/components/premium/Hero";
import { HowItWorks } from "@/components/premium/HowItWorks";
import { ProjectModeCard } from "@/components/premium/ProjectModeCard";
import { CalculatorPanel } from "@/components/premium/CalculatorPanel";
import { ResultsCompare } from "@/components/premium/ResultsCompare";
import { Trust } from "@/components/premium/Trust";
import { Cases } from "@/components/premium/Cases";
import { EngineerCTA } from "@/components/premium/EngineerCTA";
import { FAQ } from "@/components/premium/FAQ";
import { SiteFooter } from "@/components/premium/SiteFooter";
import { usePumpSelection } from "@/hooks/usePumpSelection";
import type { SelectionResult } from "@/schemas/result";
import type { WastewaterType, CorpusMaterial } from "@/schemas/input";

export default function HomePage() {
  const mutation = usePumpSelection();
  const [latest, setLatest] = useState<SelectionResult | null>(null);

  useEffect(() => {
    if (mutation.data) setLatest(mutation.data);
  }, [mutation.data]);

  const handleHeroSubmit = (Q_m3h: number) => {
    mutation.mutate({ L0: { Q_m3h } });
    setTimeout(() => {
      document.getElementById("calculator")?.scrollIntoView({ behavior: "smooth" });
    }, 200);
  };

  const handleCalcSubmit = (params: {
    Q_m3h: number;
    dH_m?: number;
    L_m?: number;
    wastewater_type?: WastewaterType;
    corpus_material?: CorpusMaterial;
  }) => {
    const req: Parameters<typeof mutation.mutate>[0] = { L0: { Q_m3h: params.Q_m3h } };
    if (params.dH_m !== undefined) req.L0.dH_m = params.dH_m;
    if (params.L_m !== undefined) req.L0.L_m = params.L_m;
    if (params.wastewater_type !== undefined) req.L0.wastewater_type = params.wastewater_type;
    if (params.corpus_material === "glass") {
      req.L1 = { corpus_material: "glass" };
    }
    mutation.mutate(req);
  };

  return (
    <>
      <SiteNav />
      <main>
        <Hero onCalculate={handleHeroSubmit} isCalculating={mutation.isPending} />
        <HowItWorks />
        <ProjectModeCard />
        <CalculatorPanel
          onSubmit={handleCalcSubmit}
          isPending={mutation.isPending}
          result={latest}
        />
        {mutation.isError && (
          <div className="bg-error/10 border-y border-error/30 py-6">
            <div className="max-w-3xl mx-auto px-5 md:px-10 text-sm text-error">
              <strong>Ошибка вызова backend:</strong>{" "}
              {mutation.error?.message ?? "неизвестная ошибка"}
              <p className="text-xs mt-1 opacity-80">
                Убедитесь, что backend запущен на http://localhost:8000 (см. README).
              </p>
            </div>
          </div>
        )}
        {latest && <ResultsCompare result={latest} />}
        <Trust />
        <Cases />
        <EngineerCTA result={latest} />
        <FAQ />
      </main>
      <SiteFooter />
    </>
  );
}
