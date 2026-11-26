"use client";

import { useEffect, useState } from "react";
import { SiteNav } from "@/components/premium/SiteNav";
import { Hero } from "@/components/premium/Hero";
import { CalculatorPanel } from "@/components/premium/CalculatorPanel";
import { EngineerCTA } from "@/components/premium/EngineerCTA";
import { FAQ } from "@/components/premium/FAQ";
import { DonateCard } from "@/components/premium/DonateCard";
import { SiteFooter } from "@/components/premium/SiteFooter";
import { usePumpSelection } from "@/hooks/usePumpSelection";
import type { SelectionResult } from "@/schemas/result";
import type { WastewaterType, CorpusMaterial } from "@/schemas/input";

export default function HomePage() {
  const mutation = usePumpSelection();
  const [quickInput, setQuickInput] = useState<{ flow: number }>();
  const [latest, setLatest] = useState<SelectionResult | null>(null);
  // Сохраняем флаг «нужно проскроллить к секции расчёта после первого расчёта».
  // Так избегаем race с setTimeout: scroll сработает строго после того,
  // как DOM-секция #calculator уже отрендерилась.
  const [pendingScroll, setPendingScroll] = useState(false);

  useEffect(() => {
    if (mutation.data) setLatest(mutation.data);
  }, [mutation.data]);

  useEffect(() => {
    if (pendingScroll && !mutation.isPending) {
      document.getElementById("calculator")?.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
        block: "start",
      });
      setPendingScroll(false);
    }
  }, [pendingScroll, mutation.isPending]);

  const handleHeroSubmit = (Q_m3h: number) => {
    setQuickInput({ flow: Q_m3h });
    mutation.mutate({ L0: { Q_m3h } });
    setPendingScroll(true);
  };

  const handleCalcSubmit = (params: {
    Q_m3h: number;
    dH_m?: number;
    L_m?: number;
    pipe_D_mm?: number;
    wastewater_type?: WastewaterType;
    corpus_material?: CorpusMaterial;
  }) => {
    const req: Parameters<typeof mutation.mutate>[0] = { L0: { Q_m3h: params.Q_m3h } };
    if (params.dH_m !== undefined) req.L0.dH_m = params.dH_m;
    if (params.L_m !== undefined) req.L0.L_m = params.L_m;
    if (params.wastewater_type !== undefined) req.L0.wastewater_type = params.wastewater_type;
    // L1 поля — pipe_D_mm критичен для расчёта Дарси-Вейсбаха
    const l1: NonNullable<Parameters<typeof mutation.mutate>[0]["L1"]> = {};
    if (params.corpus_material === "glass") l1.corpus_material = "glass";
    if (params.pipe_D_mm !== undefined) l1.pipe_D_mm = params.pipe_D_mm;
    if (Object.keys(l1).length > 0) req.L1 = l1;
    mutation.mutate(req);
  };

  return (
    <>
      <SiteNav />
      <main id="main">
        <Hero onCalculate={handleHeroSubmit} isCalculating={mutation.isPending} />
        <CalculatorPanel
          onSubmit={handleCalcSubmit}
          isPending={mutation.isPending}
          result={latest}
          resultError={mutation.isError}
          quickInput={quickInput}
        />
        <EngineerCTA result={latest} />
        <FAQ />
        <DonateCard />
      </main>
      <SiteFooter />
    </>
  );
}
