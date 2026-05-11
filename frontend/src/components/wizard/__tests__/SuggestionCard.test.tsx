import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SuggestionCard, SuggestionList } from "@/components/wizard/SuggestionCard";
import type { InputSuggestion } from "@/schemas/result";

const FULL_SUGGESTION: InputSuggestion = {
  field: "Q_m3h",
  current_value: "0.05",
  suggested_value: "3.0",
  reason: "Возможно вы ввели в л/мин — пересчёт в м³/ч.",
  reason_engineer:
    "Q = 0.05 м³/ч ≈ 0.014 л/с — на грани погрешности расходомера. Если значение в л/мин (вероятно), то 3 м³/ч; формула: Q[м³/ч] = Q[л/мин] × 0.06.",
  reason_manager:
    "Возможно вы ввели расход в литрах в минуту, а нужно в кубометрах в час. Это типичная путаница — поправьте, если так.",
  severity: "critical",
};

const FALLBACK_SUGGESTION: InputSuggestion = {
  field: "dH_m",
  current_value: "-5",
  suggested_value: "5",
  reason: "Возможно перепутан знак.",
  severity: "warning",
};

beforeEach(() => {
  // Очищаем localStorage перед каждым тестом, чтобы вкладка не «протекала».
  window.localStorage.clear();
});

describe("<SuggestionCard>", () => {
  it("показывает менеджерский текст по умолчанию", () => {
    render(<SuggestionCard suggestion={FULL_SUGGESTION} />);
    expect(
      screen.getByText(/типичная путаница/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/погрешности расходомера/i),
    ).not.toBeInTheDocument();
  });

  it("переключение на вкладку Инженер меняет текст", async () => {
    const user = userEvent.setup();
    render(<SuggestionCard suggestion={FULL_SUGGESTION} />);
    const engineerTab = screen.getByRole("tab", { name: "Инженер" });
    await user.click(engineerTab);
    expect(engineerTab).toHaveAttribute("aria-selected", "true");
    expect(
      screen.getByText(/погрешности расходомера/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/типичная путаница/i),
    ).not.toBeInTheDocument();
  });

  it("выбор вкладки сохраняется в localStorage и применяется ко второй карточке", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <>
        <SuggestionCard suggestion={FULL_SUGGESTION} />
        <SuggestionCard
          suggestion={{ ...FULL_SUGGESTION, field: "dH_m" }}
        />
      </>,
    );
    const engineerTabs = screen.getAllByRole("tab", { name: "Инженер" });
    expect(engineerTabs).toHaveLength(2);
    await user.click(engineerTabs[0]);
    // Обе карточки должны переключиться синхронно через storage event.
    for (const tab of screen.getAllByRole("tab", { name: "Инженер" })) {
      expect(tab).toHaveAttribute("aria-selected", "true");
    }
    expect(window.localStorage.getItem("preferred_suggestion_tab")).toBe(
      "engineer",
    );

    // После rerender вкладка всё равно "engineer".
    rerender(<SuggestionCard suggestion={FULL_SUGGESTION} />);
    const tab2 = screen.getByRole("tab", { name: "Инженер" });
    expect(tab2).toHaveAttribute("aria-selected", "true");
  });

  it("если reason_engineer/manager пустые — показывает fallback reason и не рисует toggle", () => {
    render(<SuggestionCard suggestion={FALLBACK_SUGGESTION} />);
    expect(screen.getByText(/перепутан знак/i)).toBeInTheDocument();
    // Toggle отсутствует — нет ролей tab.
    expect(screen.queryAllByRole("tab")).toHaveLength(0);
  });

  it("severity=critical отображается через data-severity и красный бейдж", () => {
    render(<SuggestionCard suggestion={FULL_SUGGESTION} />);
    const card = screen.getByTestId("suggestion-card");
    expect(card.dataset.severity).toBe("critical");
    expect(screen.getByText(/Обязательно проверьте/i)).toBeInTheDocument();
  });

  it("показывает локализованное имя поля и diff значений", () => {
    render(<SuggestionCard suggestion={FULL_SUGGESTION} />);
    expect(screen.getByText("Расход Q, м³/ч")).toBeInTheDocument();
    const card = screen.getByTestId("suggestion-card");
    expect(within(card).getByText("0.05")).toBeInTheDocument();
    expect(within(card).getByText("3.0")).toBeInTheDocument();
  });
});

describe("<SuggestionList>", () => {
  it("ничего не рендерит при пустом массиве", () => {
    const { container } = render(<SuggestionList suggestions={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("рендерит карточки и счётчик в заголовке", () => {
    render(
      <SuggestionList
        suggestions={[FULL_SUGGESTION, FALLBACK_SUGGESTION]}
      />,
    );
    expect(screen.getByText(/Возможно вы имели в виду · 2/i)).toBeInTheDocument();
    expect(screen.getAllByTestId("suggestion-card")).toHaveLength(2);
  });
});
