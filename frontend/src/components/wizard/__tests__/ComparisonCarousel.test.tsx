import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  ComparisonCarousel,
  computeRadarMetrics,
  computeCompositeScore,
  MiniRadar,
} from "@/components/wizard/ComparisonCarousel";
import type { PumpResult } from "@/schemas/result";

const makePump = (overrides: Partial<PumpResult> = {}): PumpResult => ({
  id: "test-pump-1",
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
  ...overrides,
});

const THREE_PUMPS: PumpResult[] = [
  makePump({
    id: "budget-1",
    brand: "ANTARUS",
    model: "ВТ-80-25",
    price_segment: "budget",
    price_estimate_rub: 650_000,
  }),
  makePump({
    id: "mid-1",
    brand: "KSB",
    model: "Amarex N S 80-220",
    price_segment: "mid",
    price_estimate_rub: 1_200_000,
    available_ru_status: "parallel_import",
  }),
  makePump({
    id: "premium-1",
    brand: "Grundfos",
    model: "SE1.80.100.40.A.Ex.4.51D",
    price_segment: "premium",
    price_estimate_rub: 2_400_000,
    available_ru_status: "stock_only",
  }),
];

describe("computeRadarMetrics", () => {
  it("даёт 6 нормализованных осей 0-100", () => {
    const m = computeRadarMetrics(THREE_PUMPS[0]);
    expect(m.bep).toBeGreaterThanOrEqual(0);
    expect(m.bep).toBeLessThanOrEqual(100);
    expect(m.eta).toBeGreaterThanOrEqual(0);
    expect(m.eta).toBeLessThanOrEqual(100);
    expect(m.h_margin).toBeGreaterThanOrEqual(0);
    expect(m.h_margin).toBeLessThanOrEqual(100);
    expect(m.availability).toBe(100); // official
    expect(m.warranty).toBeGreaterThan(0);
    expect(m.price_fit).toBe(90); // budget
  });

  it("availability снижается для parallel_import / stock_only", () => {
    const offcl = computeRadarMetrics(makePump({ available_ru_status: "official" }));
    const par = computeRadarMetrics(makePump({ available_ru_status: "parallel_import" }));
    const stock = computeRadarMetrics(makePump({ available_ru_status: "stock_only" }));
    const disc = computeRadarMetrics(makePump({ available_ru_status: "discontinued" }));
    expect(offcl.availability).toBe(100);
    expect(par.availability).toBe(60);
    expect(stock.availability).toBe(40);
    expect(disc.availability).toBe(0);
  });

  it("price_fit зависит от сегмента", () => {
    const b = computeRadarMetrics(makePump({ price_segment: "budget" }));
    const m = computeRadarMetrics(makePump({ price_segment: "mid" }));
    const p = computeRadarMetrics(makePump({ price_segment: "premium" }));
    expect(b.price_fit).toBe(90);
    expect(m.price_fit).toBe(80);
    expect(p.price_fit).toBe(70);
  });
});

describe("computeCompositeScore", () => {
  it("возвращает среднее 6 осей 0-100", () => {
    const score = computeCompositeScore({
      bep: 100,
      eta: 100,
      h_margin: 100,
      availability: 100,
      warranty: 100,
      price_fit: 100,
    });
    expect(score).toBe(100);
  });

  it("score=0 для нулевых метрик", () => {
    const score = computeCompositeScore({
      bep: 0,
      eta: 0,
      h_margin: 0,
      availability: 0,
      warranty: 0,
      price_fit: 0,
    });
    expect(score).toBe(0);
  });
});

describe("<MiniRadar>", () => {
  it("рендерит 6 осей", () => {
    const m = computeRadarMetrics(THREE_PUMPS[0]);
    render(<MiniRadar metrics={m} />);
    const radar = screen.getByTestId("mini-radar");
    expect(radar).toBeInTheDocument();
    // 6 подписей осей
    expect(screen.getByTestId("radar-axis-bep")).toBeInTheDocument();
    expect(screen.getByTestId("radar-axis-eta")).toBeInTheDocument();
    expect(screen.getByTestId("radar-axis-h_margin")).toBeInTheDocument();
    expect(screen.getByTestId("radar-axis-availability")).toBeInTheDocument();
    expect(screen.getByTestId("radar-axis-warranty")).toBeInTheDocument();
    expect(screen.getByTestId("radar-axis-price_fit")).toBeInTheDocument();
  });
});

describe("<ComparisonCarousel>", () => {
  it("рендерит 3 карточки насосов", () => {
    render(<ComparisonCarousel pumps={THREE_PUMPS} />);
    // Каждая карточка появляется и в desktop-grid, и в mobile-carousel
    // (jsdom не применяет CSS-классы hidden/md:grid → оба видны).
    expect(screen.getAllByTestId("compare-card-budget-1").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByTestId("compare-card-mid-1").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByTestId("compare-card-premium-1").length).toBeGreaterThanOrEqual(1);
  });

  it("показывает brand и model на каждой карточке", () => {
    render(<ComparisonCarousel pumps={THREE_PUMPS} />);
    // ANTARUS, KSB, Grundfos появляются дважды (desktop+mobile рендерится одновременно)
    expect(screen.getAllByText("ANTARUS").length).toBeGreaterThan(0);
    expect(screen.getAllByText("KSB").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Grundfos").length).toBeGreaterThan(0);
  });

  it("показывает composite score badge на каждой карточке", () => {
    render(<ComparisonCarousel pumps={THREE_PUMPS} />);
    // Минимум 3 badge-а (по одному на карточку в desktop view)
    const badges = screen.getAllByTestId(/^composite-/);
    expect(badges.length).toBeGreaterThanOrEqual(3);
    badges.forEach((b) => {
      expect(b.textContent).toMatch(/\d+%/);
    });
  });

  it("rendered radar содержит 6 осей у каждой карточки", () => {
    render(<ComparisonCarousel pumps={THREE_PUMPS} />);
    const radars = screen.getAllByTestId("mini-radar");
    expect(radars.length).toBeGreaterThanOrEqual(3);
    // на любом из них найдутся подписи осей
    const firstRadar = radars[0];
    expect(within(firstRadar).getByText("BEP")).toBeInTheDocument();
    expect(within(firstRadar).getByText("η")).toBeInTheDocument();
    expect(within(firstRadar).getByText("H")).toBeInTheDocument();
    expect(within(firstRadar).getByText("Дост.")).toBeInTheDocument();
    expect(within(firstRadar).getByText("Гар.")).toBeInTheDocument();
    expect(within(firstRadar).getByText("Цена")).toBeInTheDocument();
  });

  it("клик «Выбрать» вызывает onSelect с правильным насосом", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<ComparisonCarousel pumps={THREE_PUMPS} onSelect={onSelect} />);
    // Берём первую кнопку «Выбрать» для mid-1 (rendered и в desktop и в mobile,
    // userEvent кликает первую попавшуюся)
    const selectButtons = screen.getAllByTestId("select-mid-1");
    await user.click(selectButtons[0]);
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: "mid-1", brand: "KSB" }),
    );
  });

  it("активная карточка имеет надпись «Выбран»", () => {
    render(<ComparisonCarousel pumps={THREE_PUMPS} activePumpId="mid-1" />);
    const selectButtons = screen.getAllByTestId("select-mid-1");
    expect(selectButtons[0].textContent).toMatch(/Выбран/);
  });

  it("заглушка при пустом массиве", () => {
    render(<ComparisonCarousel pumps={[]} />);
    expect(screen.getByText(/Нет насосов для сравнения/i)).toBeInTheDocument();
  });

  it("mobile carousel: touch-swipe влево переключает на следующий слайд", () => {
    render(<ComparisonCarousel pumps={THREE_PUMPS} />);
    const track = screen.getByTestId("mobile-carousel-track");
    // Симулируем swipe влево (dx = -100)
    fireEvent.touchStart(track, {
      touches: [{ clientX: 200, clientY: 100 }],
    });
    fireEvent.touchEnd(track, {
      changedTouches: [{ clientX: 80, clientY: 100 }],
    });
    // После свайпа второй dot должен быть aria-selected=true
    const dot1 = screen.getByTestId("carousel-dot-1");
    expect(dot1).toHaveAttribute("aria-selected", "true");
  });

  it("mobile carousel: клик на dot переключает слайд", async () => {
    const user = userEvent.setup();
    render(<ComparisonCarousel pumps={THREE_PUMPS} />);
    const dot2 = screen.getByTestId("carousel-dot-2");
    await user.click(dot2);
    expect(dot2).toHaveAttribute("aria-selected", "true");
  });

  it("работает с 4+ насосами (не только 3)", () => {
    const four = [...THREE_PUMPS, makePump({ id: "extra-1", brand: "Wilo", model: "Rexa" })];
    render(<ComparisonCarousel pumps={four} />);
    expect(screen.getAllByTestId("compare-card-extra-1").length).toBeGreaterThanOrEqual(1);
    // 4 dots в mobile carousel
    expect(screen.getByTestId("carousel-dot-3")).toBeInTheDocument();
  });
});
