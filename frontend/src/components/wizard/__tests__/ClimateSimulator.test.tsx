import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ClimateSimulator } from "@/components/wizard/ClimateSimulator";

const CITIES_LIST = {
  cities: [
    {
      city: "Краснодар", region: "Краснодарский край", climate_zone: "IIIB",
      altitude_m: 25, frost_depth_mm: 800, t_min_5pct_c: -19, lat: 45.04, lon: 38.97,
    },
    {
      city: "Норильск", region: "Красноярский край", climate_zone: "IA",
      altitude_m: 90, frost_depth_mm: 2500, t_min_5pct_c: -45, lat: 69.35, lon: 88.18,
    },
  ],
  count: 2,
};

const NORILSK_CARD = {
  climate: {
    city: "Норильск", region: "Красноярский край", climate_zone: "IA",
    altitude_m: 90, frost_depth_mm: 2500, t_min_5pct_c: -45, lat: 69.35, lon: 88.18,
  },
  recommendations: [
    {
      code: "heating_cable_required",
      severity: "critical",
      title: "Греющий кабель обязателен",
      text: "T_min < −30°C → нужен подогрев напорных линий",
    },
    {
      code: "cabinet_uhl1_required",
      severity: "warning",
      title: "Шкаф ХЛ1",
      text: "Климатическое исполнение УХЛ1",
    },
  ],
};

beforeEach(() => {
  window.localStorage.clear();
  globalThis.fetch = vi.fn((url: string | URL) => {
    const u = typeof url === "string" ? url : url.toString();
    if (u.includes("/climate/cities")) {
      return Promise.resolve(
        new Response(JSON.stringify(CITIES_LIST), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }
    if (u.includes("/climate/")) {
      return Promise.resolve(
        new Response(JSON.stringify(NORILSK_CARD), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }
    return Promise.reject(new Error("unexpected url: " + u));
  }) as unknown as typeof fetch;
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("<ClimateSimulator>", () => {
  it("загружает список городов и показывает в datalist", async () => {
    render(<ClimateSimulator />);
    await waitFor(() => {
      const options = document.querySelectorAll("#climate-city-list option");
      expect(options.length).toBe(2);
    });
  });

  it("при выборе города показывает карточку климата + рекомендации", async () => {
    const user = userEvent.setup();
    render(<ClimateSimulator value="" />);
    await waitFor(() => {
      expect(document.querySelectorAll("#climate-city-list option").length).toBe(2);
    });
    const input = screen.getByLabelText("Город (для climate-рекомендаций)") as HTMLInputElement;
    await user.clear(input);
    await user.type(input, "Норильск");

    await waitFor(() => {
      expect(screen.getByTestId("climate-card")).toBeInTheDocument();
    });
    expect(screen.getByTestId("climate-recommendations")).toBeInTheDocument();
    expect(screen.getByText(/Греющий кабель обязателен/)).toBeInTheDocument();
    expect(screen.getByText(/-45 °C/)).toBeInTheDocument();
  });

  it("вызывает onChange с altitude_m когда город найден", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ClimateSimulator value="" onChange={onChange} />);
    await waitFor(() => {
      expect(document.querySelectorAll("#climate-city-list option").length).toBe(2);
    });
    const input = screen.getByLabelText("Город (для climate-рекомендаций)") as HTMLInputElement;
    await user.type(input, "Норильск");
    await waitFor(() => {
      expect(screen.getByTestId("climate-card")).toBeInTheDocument();
    });
    // onChange был вызван с (city, altitude) после совпадения
    const calls = onChange.mock.calls;
    const withAltitude = calls.find((c) => c[1] === 90);
    expect(withAltitude).toBeDefined();
  });
});
