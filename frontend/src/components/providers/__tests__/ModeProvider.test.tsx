import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  ModeProvider,
  useMode,
  MODE_STORAGE_KEY,
  type AppMode,
} from "@/components/providers/ModeProvider";
import { ModeToggle } from "@/components/providers/ModeToggle";

/**
 * Маленький тестовый-консьюмер для чтения значения из контекста.
 */
function ModeDisplay() {
  const { mode, setMode, toggle } = useMode();
  return (
    <div>
      <span data-testid="mode-value">{mode}</span>
      <button data-testid="set-engineer" onClick={() => setMode("engineer")}>
        set engineer
      </button>
      <button data-testid="set-manager" onClick={() => setMode("manager")}>
        set manager
      </button>
      <button data-testid="toggle" onClick={toggle}>
        toggle
      </button>
    </div>
  );
}

beforeEach(() => {
  window.localStorage.clear();
});

describe("<ModeProvider>", () => {
  it("default mode = manager", () => {
    render(
      <ModeProvider>
        <ModeDisplay />
      </ModeProvider>,
    );
    expect(screen.getByTestId("mode-value").textContent).toBe("manager");
  });

  it("initialMode сохраняется в localStorage и видим в context", () => {
    render(
      <ModeProvider initialMode="engineer">
        <ModeDisplay />
      </ModeProvider>,
    );
    expect(screen.getByTestId("mode-value").textContent).toBe("engineer");
    expect(window.localStorage.getItem(MODE_STORAGE_KEY)).toBe("engineer");
  });

  it("setMode меняет context и пишет в localStorage", async () => {
    const user = userEvent.setup();
    render(
      <ModeProvider>
        <ModeDisplay />
      </ModeProvider>,
    );
    await user.click(screen.getByTestId("set-engineer"));
    expect(screen.getByTestId("mode-value").textContent).toBe("engineer");
    expect(window.localStorage.getItem(MODE_STORAGE_KEY)).toBe("engineer");
    await user.click(screen.getByTestId("set-manager"));
    expect(screen.getByTestId("mode-value").textContent).toBe("manager");
    expect(window.localStorage.getItem(MODE_STORAGE_KEY)).toBe("manager");
  });

  it("toggle переключает manager ↔ engineer", async () => {
    const user = userEvent.setup();
    render(
      <ModeProvider>
        <ModeDisplay />
      </ModeProvider>,
    );
    expect(screen.getByTestId("mode-value").textContent).toBe("manager");
    await user.click(screen.getByTestId("toggle"));
    expect(screen.getByTestId("mode-value").textContent).toBe("engineer");
    await user.click(screen.getByTestId("toggle"));
    expect(screen.getByTestId("mode-value").textContent).toBe("manager");
  });

  it("setMode синхронизирует preferred_suggestion_tab (однонаправленно)", async () => {
    const user = userEvent.setup();
    render(
      <ModeProvider>
        <ModeDisplay />
      </ModeProvider>,
    );
    await user.click(screen.getByTestId("set-engineer"));
    expect(window.localStorage.getItem("preferred_suggestion_tab")).toBe(
      "engineer",
    );
    await user.click(screen.getByTestId("set-manager"));
    expect(window.localStorage.getItem("preferred_suggestion_tab")).toBe(
      "manager",
    );
  });

  it("несколько ModeDisplay в одном дереве остаются синхронны", async () => {
    const user = userEvent.setup();
    render(
      <ModeProvider>
        <ModeDisplay />
        <ModeDisplay />
      </ModeProvider>,
    );
    const values = screen.getAllByTestId("mode-value");
    expect(values.map((el) => el.textContent)).toEqual(["manager", "manager"]);
    await user.click(screen.getAllByTestId("set-engineer")[0]);
    expect(screen.getAllByTestId("mode-value").map((el) => el.textContent)).toEqual(
      ["engineer", "engineer"],
    );
  });

  it("persist: предзаписанное значение в localStorage подхватывается при mount", () => {
    window.localStorage.setItem(MODE_STORAGE_KEY, "engineer");
    render(
      <ModeProvider>
        <ModeDisplay />
      </ModeProvider>,
    );
    expect(screen.getByTestId("mode-value").textContent).toBe("engineer");
  });

  it("storage event из другой вкладки обновляет state", () => {
    render(
      <ModeProvider>
        <ModeDisplay />
      </ModeProvider>,
    );
    expect(screen.getByTestId("mode-value").textContent).toBe("manager");
    act(() => {
      window.localStorage.setItem(MODE_STORAGE_KEY, "engineer");
      // Симулируем storage event как будто пришёл из другой вкладки.
      window.dispatchEvent(
        new StorageEvent("storage", {
          key: MODE_STORAGE_KEY,
          newValue: "engineer",
          oldValue: "manager",
          storageArea: window.localStorage,
        }),
      );
    });
    expect(screen.getByTestId("mode-value").textContent).toBe("engineer");
  });

  it("useMode без провайдера: fallback через localStorage", () => {
    // Без <ModeProvider> вокруг — useMode должен использовать fallback.
    window.localStorage.setItem(MODE_STORAGE_KEY, "engineer");
    render(<ModeDisplay />);
    expect(screen.getByTestId("mode-value").textContent).toBe("engineer");
  });

  it("игнорирует мусор в localStorage", () => {
    window.localStorage.setItem(MODE_STORAGE_KEY, "garbage" as AppMode);
    render(
      <ModeProvider>
        <ModeDisplay />
      </ModeProvider>,
    );
    expect(screen.getByTestId("mode-value").textContent).toBe("manager");
  });
});

describe("<ModeToggle>", () => {
  it("рендерит две radio-кнопки с aria-checked", () => {
    render(
      <ModeProvider>
        <ModeToggle />
      </ModeProvider>,
    );
    const managerBtn = screen.getByRole("radio", { name: /Менеджер/i });
    const engineerBtn = screen.getByRole("radio", { name: /Инженер/i });
    expect(managerBtn).toHaveAttribute("aria-checked", "true");
    expect(engineerBtn).toHaveAttribute("aria-checked", "false");
  });

  it("клик по «Инженер» переключает aria-checked и пишет в localStorage", async () => {
    const user = userEvent.setup();
    render(
      <ModeProvider>
        <ModeToggle />
      </ModeProvider>,
    );
    await user.click(screen.getByRole("radio", { name: /Инженер/i }));
    expect(
      screen.getByRole("radio", { name: /Инженер/i }),
    ).toHaveAttribute("aria-checked", "true");
    expect(
      screen.getByRole("radio", { name: /Менеджер/i }),
    ).toHaveAttribute("aria-checked", "false");
    expect(window.localStorage.getItem(MODE_STORAGE_KEY)).toBe("engineer");
  });

  it("Provider + ModeDisplay + ModeToggle переключаются синхронно", async () => {
    const user = userEvent.setup();
    render(
      <ModeProvider>
        <ModeDisplay />
        <ModeToggle />
      </ModeProvider>,
    );
    await user.click(screen.getByRole("radio", { name: /Инженер/i }));
    expect(screen.getByTestId("mode-value").textContent).toBe("engineer");
  });
});
