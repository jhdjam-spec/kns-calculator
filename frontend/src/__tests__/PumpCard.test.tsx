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
  price_estimate_rub: 837_000,
  price_breakdown: {
    pump_rub: 150_000,
    atm_rub: 45_400,
    valve_rub: 26_400,
    check_valve_rub: 13_200,
    rails_rub: 24_000,
    cabinet_rub: 200_000,
    floats_rub: 20_000,
    chain_rub: 8_000,
    corpus_rub: 350_000,
    total_rub: 837_000,
    total_low_rub: 750_000,
    total_high_rub: 920_000,
  },
  price_confidence: "medium",
};

describe("<PumpCard>", () => {
  it("рендерит данные насоса", () => {
    render(<PumpCard segment="budget" pump={SAMPLE_PUMP} />);
    expect(screen.getByText("KAIQUAN")).toBeInTheDocument();
    expect(screen.getByText("50WQ/S 20-22-3")).toBeInTheDocument();
    expect(screen.getByText("3 кВт")).toBeInTheDocument();
    expect(screen.getByText("50 мм")).toBeInTheDocument();
    // Новый русский бейдж доступности
    expect(screen.getByText(/Официальная поставка/i)).toBeInTheDocument();
    // POR теперь отображается как "Оптимально"
    expect(screen.getByText("Оптимально")).toBeInTheDocument();
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

  it("выводит совпадение в процентах вместо score", () => {
    render(<PumpCard segment="budget" pump={SAMPLE_PUMP} />);
    // 0.671 → 67%
    expect(screen.getByText(/67%/)).toBeInTheDocument();
  });

  it("показывает оценочную цену комплекта в рублях", () => {
    render(<PumpCard segment="budget" pump={SAMPLE_PUMP} />);
    expect(screen.getByText(/837\s*000\s*₽/)).toBeInTheDocument();
    // Confidence label теперь "по прайсу 2026"
    expect(screen.getByText(/по прайсу 2026/i)).toBeInTheDocument();
  });

  it("не показывает блок цены если price_estimate_rub = 0", () => {
    render(
      <PumpCard
        segment="mid"
        pump={{ ...SAMPLE_PUMP, price_estimate_rub: 0 }}
      />
    );
    expect(screen.queryByText(/Ориентировочно комплект/i)).not.toBeInTheDocument();
  });
});
