import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CostSankey } from "@/components/wizard/CostSankey";
import type { PumpResult } from "@/schemas/result";

function makePump(): PumpResult {
  return {
    id: "p1",
    brand: "Pedrollo",
    model: "BCm 15/50-N",
    type: "submersible_sewage",
    impeller: "vortex",
    free_passage_mm: 40,
    envelope: {
      Q_min_m3h: 5, Q_max_m3h: 30, H_min_m: 2, H_max_m: 18,
      Q_BEP_m3h: 18, H_BEP_m: 12, eta_BEP_pct: 55, NPSHr_at_BEP_m: 2.5,
    },
    P_kW: 1.5,
    discharge_DN_mm: 50,
    price_segment: "budget",
    available_ru_status: "official",
    score: 0.78,
    score_breakdown: {},
    score_explanation: {},
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
  };
}

const TCO_RESPONSE = {
  horizon_years: 10,
  operating_mode: "level_based",
  hours_per_year: 2628,
  tariff_rub_per_kwh: 7.5,
  capex: {
    pump_rub: 70000, corpus_rub: 0, cabinet_rub: 12000, fittings_rub: 28000,
    install_rub: 11000, transport_rub: 3300, anti_buoyancy_rub: 0, total_rub: 124300,
  },
  opex_annual: {
    electricity_rub: 29565, maintenance_rub: 3500, depreciation_rub: 8750,
    cleaning_rub: 60000, electronics_rub: 240, total_annual_rub: 102055,
  },
  opex_horizon_rub: 1020550,
  tco_horizon_rub: 1144850,
  flow_horizon_m3: 473040,
  cost_per_m3_rub: 2.42,
  sankey_nodes: [],
  sankey_links: [],
  pump_meta: { brand: "Pedrollo", model: "BCm 15/50-N", P_kW: 1.5, segment: "budget" },
};

beforeEach(() => {
  window.localStorage.clear();
  globalThis.fetch = vi.fn(
    () =>
      Promise.resolve(
        new Response(JSON.stringify(TCO_RESPONSE), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ) as unknown as ReturnType<typeof fetch>,
  ) as unknown as typeof fetch;
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("<CostSankey>", () => {
  it("не рендерится если open=false", () => {
    render(<CostSankey pump={makePump()} segment="budget" open={false} onClose={() => {}} />);
    expect(screen.queryByTestId("cost-sankey")).not.toBeInTheDocument();
  });

  it("вызывает /tco/calculate и показывает cost_per_m3 + TCO", async () => {
    render(<CostSankey pump={makePump()} segment="budget" open={true} onClose={() => {}} />);
    expect(screen.getByTestId("cost-sankey")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("sankey-view")).toBeInTheDocument();
    });
    // Стоимость 1 м³
    expect(screen.getByText(/2\.42 ₽/)).toBeInTheDocument();
    // Tabs горизонта
    expect(screen.getByTestId("horizon-1")).toBeInTheDocument();
    expect(screen.getByTestId("horizon-5")).toBeInTheDocument();
    expect(screen.getByTestId("horizon-10")).toBeInTheDocument();
  });

  it("позволяет переключить горизонт и пересчитать", async () => {
    const user = userEvent.setup();
    render(<CostSankey pump={makePump()} segment="budget" open={true} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByTestId("sankey-view")).toBeInTheDocument());
    const fetchMock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>;
    const callsBefore = fetchMock.mock.calls.length;
    await user.click(screen.getByTestId("horizon-1"));
    await waitFor(() => {
      expect((globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(callsBefore);
    });
  });

  it("содержит disclaimer ±30%", async () => {
    render(<CostSankey pump={makePump()} segment="budget" open={true} onClose={() => {}} />);
    expect(screen.getByText(/±30%/)).toBeInTheDocument();
  });
});
