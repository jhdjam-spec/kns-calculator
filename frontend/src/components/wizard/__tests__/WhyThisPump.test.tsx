import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WhyThisPump } from "@/components/wizard/WhyThisPump";
import type { PumpResult } from "@/schemas/result";

// Минимальный реалистичный PumpResult с score_explanation, как возвращает backend
// (см. backend/pump_calculator/matching.py::build_score_explanation).
function makePump(overrides: Partial<PumpResult> = {}): PumpResult {
  return {
    id: "test-pump-1",
    brand: "Pedrollo",
    model: "VXm 15/50-N",
    type: "submersible_sewage",
    impeller: "vortex",
    free_passage_mm: 40,
    envelope: {
      Q_min_m3h: 5,
      Q_max_m3h: 30,
      H_min_m: 2,
      H_max_m: 18,
      Q_BEP_m3h: 18,
      H_BEP_m: 12,
      eta_BEP_pct: 55,
      NPSHr_at_BEP_m: 2.5,
    },
    P_kW: 1.5,
    discharge_DN_mm: 50,
    price_segment: "budget",
    available_ru_status: "official",
    score: 0.78,
    score_breakdown: {},
    score_explanation: {
      step_1_filter: "Прошёл фильтр: wastewater_type=domestic, free_passage=40 мм ≥ 40 мм требуемых",
      step_2_envelope: "Q=18 м³/ч в диапазоне [5, 30]; H_full=12 м ≤ H_max=18 м",
      step_3_aor: "Работа в pulsed-режиме (циклы вкл/выкл по поплавкам)",
      step_5_segment: "#1 из 5 кандидатов сегмента budget",
      rank_in_segment: 1,
      candidates_in_segment: 5,
      step_4_composite_sum: 0.82,
      step_4_final_score: 0.78,
      step_4_composite: {
        bep_proximity: {
          value: 1.0,
          weight: 0.4,
          contribution: 0.4,
          label: "Близость к BEP",
          hint_engineer: "bep_prox = max(0, 1 - |18 - 18|/18) = 1.000",
          hint_manager: "Насколько близко рабочая точка к идеалу: 100%",
        },
        eta: {
          value: 0.55,
          weight: 0.25,
          contribution: 0.1375,
          label: "КПД в BEP",
          hint_engineer: "η_BEP = 55%",
          hint_manager: "Эффективность насоса 55% — влияет на счёт за электричество",
        },
      },
      citations: [
        { text: "СП 32.13330.2018 §6.5", url: "https://docs.cntd.ru/document/554404696" },
      ],
    },
    duty_point: { Q_m3h: 18, H_m: 12 },
    aor_zone: "POR",
    notes: [],
    price_estimate_rub: 110000,
    price_breakdown: {
      pump_rub: 70000, atm_rub: 8000, valve_rub: 6000, check_valve_rub: 6000,
      rails_rub: 5000, cabinet_rub: 12000, floats_rub: 3000, chain_rub: 0,
      corpus_rub: 0, total_rub: 110000, total_low_rub: 99000, total_high_rub: 121000,
    },
    price_confidence: "medium",
    ...overrides,
  };
}

beforeEach(() => {
  window.localStorage.clear();
});

describe("<WhyThisPump>", () => {
  it("не отображается, если open=false", () => {
    const pump = makePump();
    render(<WhyThisPump pump={pump} open={false} onClose={() => {}} />);
    expect(screen.queryByTestId("why-this-pump")).not.toBeInTheDocument();
  });

  it("показывает 5 шагов и итоговый score при open=true", () => {
    const pump = makePump();
    render(<WhyThisPump pump={pump} open={true} onClose={() => {}} />);
    expect(screen.getByTestId("why-this-pump")).toBeInTheDocument();
    expect(screen.getByTestId("why-steps")).toBeInTheDocument();
    // Шаги 1, 2, 3, 4, 5
    expect(screen.getByText(/Фильтр по типу стоков/)).toBeInTheDocument();
    expect(screen.getByText(/Q-H envelope/)).toBeInTheDocument();
    expect(screen.getByText(/POR \/ AOR/)).toBeInTheDocument();
    expect(screen.getByText(/Композитный score/)).toBeInTheDocument();
    expect(screen.getByText(/Выбор сегмента/)).toBeInTheDocument();
    // Финальный score
    expect(screen.getByText(/78\.0%/)).toBeInTheDocument();
    // Метка ранга в сегменте — встречается дважды (в сводке и в шаге 5)
    const rankMatches = screen.getAllByText(/#1 из 5/);
    expect(rankMatches.length).toBeGreaterThanOrEqual(1);
  });

  it("показывает композит-факторы с bar и контрибьюцией", () => {
    const pump = makePump();
    render(<WhyThisPump pump={pump} open={true} onClose={() => {}} />);
    const factors = screen.getByTestId("why-factors");
    expect(factors).toBeInTheDocument();
    expect(factors.querySelectorAll("[data-factor]")).toHaveLength(2);
    expect(screen.getByText("Близость к BEP")).toBeInTheDocument();
    expect(screen.getByText("КПД в BEP")).toBeInTheDocument();
  });

  it("показывает менеджерский hint по умолчанию (mode=manager — default)", () => {
    const pump = makePump();
    render(<WhyThisPump pump={pump} open={true} onClose={() => {}} />);
    // По умолчанию режим manager → видим manager hint
    expect(screen.getByText(/Насколько близко рабочая точка к идеалу: 100%/)).toBeInTheDocument();
    // Engineer hint скрыт
    expect(screen.queryByText(/bep_prox = max/)).not.toBeInTheDocument();
  });

  it("при mode=engineer переключает на инженерные hint'ы", () => {
    window.localStorage.setItem("kns_global_mode", "engineer");
    const pump = makePump();
    render(<WhyThisPump pump={pump} open={true} onClose={() => {}} />);
    expect(screen.getByText(/bep_prox = max\(0, 1 -/)).toBeInTheDocument();
    expect(screen.getByText(/η_BEP = 55%/)).toBeInTheDocument();
  });

  it("вызывает onClose при клике на крестик", async () => {
    const user = userEvent.setup();
    const onClose = (): void => {
      closeCalls += 1;
    };
    let closeCalls = 0;
    const pump = makePump();
    render(<WhyThisPump pump={pump} open={true} onClose={onClose} />);
    const closeBtns = screen.getAllByRole("button", { name: "Закрыть" });
    await user.click(closeBtns[closeBtns.length - 1]);
    expect(closeCalls).toBeGreaterThan(0);
  });

  it("показывает цитаты СП когда они есть", () => {
    const pump = makePump();
    render(<WhyThisPump pump={pump} open={true} onClose={() => {}} />);
    expect(screen.getByTestId("why-citations")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /СП 32.13330.2018/ });
    expect(link).toHaveAttribute("href", "https://docs.cntd.ru/document/554404696");
  });
});
