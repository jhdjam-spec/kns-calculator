import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PumpCard } from "@/components/PumpCard";
import type { PumpResult } from "@/schemas/result";

const SAMPLE_PUMP: PumpResult = {
  id: "kaiquan-50wqs202-3",
  brand: "KAIQUAN",
  model: "50WQ/S 20-22-3",
  type: "submersible_sewage",
  impeller: "vortex",
  free_passage_mm: 50,
  envelope: {
    Q_min_m3h: 5,
    Q_max_m3h: 30,
    H_min_m: 8,
    H_max_m: 25,
    Q_BEP_m3h: 22.9,
    H_BEP_m: 17.4,
    eta_BEP_pct: 46.4,
  },
  P_kW: 3,
  discharge_DN_mm: 50,
  price_segment: "budget",
  available_ru_status: "official",
  score: 0.671,
  score_breakdown: {},
  duty_point: { Q_m3h: 21.2, H_m: 12.6 },
  aor_zone: "POR",
  notes: [],
};

describe("<PumpCard>", () => {
  it("рендерит данные насоса", () => {
    render(<PumpCard segment="budget" pump={SAMPLE_PUMP} />);
    expect(screen.getByText("KAIQUAN")).toBeInTheDocument();
    expect(screen.getByText("50WQ/S 20-22-3")).toBeInTheDocument();
    expect(screen.getByText("3 кВт")).toBeInTheDocument();
    expect(screen.getByText("50 мм")).toBeInTheDocument();
    expect(screen.getByText(/официально в РФ/i)).toBeInTheDocument();
    expect(screen.getByText("POR")).toBeInTheDocument();
  });

  it("показывает заголовок 'Бюджет' для segment=budget", () => {
    render(<PumpCard segment="budget" pump={SAMPLE_PUMP} />);
    expect(screen.getByText("Бюджет")).toBeInTheDocument();
  });

  it("показывает заглушку при pump=null", () => {
    render(<PumpCard segment="premium" pump={null} />);
    expect(screen.getByText("Премиум")).toBeInTheDocument();
    expect(screen.getByText(/Нет подходящих кандидатов/i)).toBeInTheDocument();
  });

  it("выводит score с двумя знаками после запятой", () => {
    render(<PumpCard segment="budget" pump={SAMPLE_PUMP} />);
    expect(screen.getByText(/0.67/)).toBeInTheDocument();
  });
});
