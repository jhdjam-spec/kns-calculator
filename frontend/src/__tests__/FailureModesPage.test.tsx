import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FailureModesPage from "@/app/teach/failure-modes/page";

const MODES_LIST = {
  count: 2,
  categories: ["hydraulic", "operational"],
  filter: { trigger: null, category: null, severity: null },
  modes: [
    {
      id: "cavitation_impeller",
      name: "Кавитация рабочего колеса",
      category: "hydraulic",
      severity: "high",
      symptoms: ["Шум как гравий в трубе", "Вибрация корпуса"],
      causes: ["NPSHa < NPSHr"],
      prevention: ["Расчёт NPSHa с запасом"],
      fix_cost_rub: [50000, 200000],
      downtime_hours: [24, 72],
      lifecycle_impact: "Снижение срока службы в 2-3 раза",
      trigger_in_calculator: "auto_npsh_low",
      sp_norm: "СП 32.13330 §6.5",
    },
    {
      id: "dry_run",
      name: "Сухой ход",
      category: "operational",
      severity: "critical",
      symptoms: ["Резкий рост температуры корпуса"],
      causes: ["Отказ датчика уровня"],
      prevention: ["Два независимых датчика"],
      fix_cost_rub: [80000, 400000],
      downtime_hours: [48, 168],
      lifecycle_impact: "Полный выход из строя мехуплотнения",
      trigger_in_calculator: "auto_dry_run_risk",
      sp_norm: "ГОСТ Р 53674 §5.4",
    },
  ],
};

const FILTERED_HIGH = { ...MODES_LIST, count: 1, modes: [MODES_LIST.modes[0]] };

// Mock SiteNav/SiteFooter (они тянут tonnu контекста премиум-страницы)
vi.mock("@/components/premium/SiteNav", () => ({
  SiteNav: () => <nav data-testid="sitenav-mock" />,
}));
vi.mock("@/components/premium/SiteFooter", () => ({
  SiteFooter: () => <footer data-testid="sitefooter-mock" />,
}));

beforeEach(() => {
  globalThis.fetch = vi.fn((url: string | URL) => {
    const u = typeof url === "string" ? url : url.toString();
    if (u.includes("severity=high")) {
      return Promise.resolve(
        new Response(JSON.stringify(FILTERED_HIGH), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }
    return Promise.resolve(
      new Response(JSON.stringify(MODES_LIST), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
  }) as unknown as typeof fetch;
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("FailureModesPage /teach/failure-modes", () => {
  it("загружает каталог и показывает 2 карточки в сетке", async () => {
    render(<FailureModesPage />);
    await waitFor(() => {
      expect(screen.getByTestId("failure-grid")).toBeInTheDocument();
    });
    expect(screen.getByTestId("mode-card-cavitation_impeller")).toBeInTheDocument();
    expect(screen.getByTestId("mode-card-dry_run")).toBeInTheDocument();
    expect(screen.getByText(/Найдено: 2 режимов/)).toBeInTheDocument();
  });

  it("открывает drawer при клике на карточку и показывает детали", async () => {
    const user = userEvent.setup();
    render(<FailureModesPage />);
    await waitFor(() => {
      expect(screen.getByTestId("mode-card-cavitation_impeller")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("mode-card-cavitation_impeller"));
    expect(screen.getByTestId("failure-drawer")).toBeInTheDocument();
    expect(screen.getByText(/NPSHa < NPSHr/)).toBeInTheDocument();
    expect(screen.getByText(/Снижение срока службы в 2-3 раза/)).toBeInTheDocument();
  });

  it("фильтрует по severity при клике на бейдж", async () => {
    const user = userEvent.setup();
    render(<FailureModesPage />);
    await waitFor(() => {
      expect(screen.getByTestId("failure-grid")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("severity-high"));
    await waitFor(() => {
      expect(screen.getByText(/Найдено: 1 режимов/)).toBeInTheDocument();
    });
    expect(screen.queryByTestId("mode-card-dry_run")).not.toBeInTheDocument();
  });

  it("закрывается drawer по клику на крестик", async () => {
    const user = userEvent.setup();
    render(<FailureModesPage />);
    await waitFor(() => {
      expect(screen.getByTestId("mode-card-dry_run")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("mode-card-dry_run"));
    expect(screen.getByTestId("failure-drawer")).toBeInTheDocument();
    const closeBtns = screen.getAllByRole("button", { name: "Закрыть" });
    await user.click(closeBtns[closeBtns.length - 1]);
    await waitFor(() => {
      expect(screen.queryByTestId("failure-drawer")).not.toBeInTheDocument();
    });
  });
});
