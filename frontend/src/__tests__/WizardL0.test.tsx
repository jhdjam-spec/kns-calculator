import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WizardL0 } from "@/components/WizardL0";

describe("<WizardL0>", () => {
  it("рендерит 4 поля и кнопку", () => {
    render(<WizardL0 onSubmit={() => {}} />);

    // Поле расхода ищем по id (label "Расход" есть и у группы — не уникален)
    expect(document.getElementById("Q_value")).toBeInTheDocument();
    expect(screen.getByLabelText(/Перепад точек/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Длина напорной трассы/i)).toBeInTheDocument();
    expect(screen.getByText(/Тип стоков/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Подобрать насос/i })).toBeInTheDocument();
  });

  it("при сабмите валидной формы вызывает onSubmit с L0Input", async () => {
    const user = userEvent.setup();
    const handle = vi.fn();
    render(<WizardL0 onSubmit={handle} />);

    await user.type(document.getElementById("Q_value")!, "21.2");
    await user.type(screen.getByLabelText(/Перепад точек/i), "10");
    await user.type(screen.getByLabelText(/Длина напорной трассы/i), "0");
    await user.click(screen.getByRole("button", { name: /Подобрать насос/i }));

    await waitFor(() => {
      expect(handle).toHaveBeenCalledTimes(1);
    });
    expect(handle.mock.calls[0][0]).toEqual({
      Q_m3h: 21.2,
      dH_m: 10,
      L_m: 0,
      wastewater_type: "domestic",
    });
  });

  it("блокирует сабмит при пустых полях", async () => {
    const user = userEvent.setup();
    const handle = vi.fn();
    render(<WizardL0 onSubmit={handle} />);

    await user.click(screen.getByRole("button", { name: /Подобрать насос/i }));

    expect(handle).not.toHaveBeenCalled();
  });

  it("конвертирует л/с → м³/ч при выборе единицы", async () => {
    const user = userEvent.setup();
    const handle = vi.fn();
    render(<WizardL0 onSubmit={handle} />);

    await user.type(document.getElementById("Q_value")!, "5.9");
    await user.selectOptions(screen.getByLabelText(/Единицы расхода/i), "ls");
    await user.type(screen.getByLabelText(/Перепад точек/i), "10");
    await user.type(screen.getByLabelText(/Длина напорной трассы/i), "0");
    await user.click(screen.getByRole("button", { name: /Подобрать насос/i }));

    await waitFor(() => expect(handle).toHaveBeenCalled());
    const arg = handle.mock.calls[0][0];
    expect(arg.Q_m3h).toBeCloseTo(21.24, 2);
  });

  it("отображает 'Подбираю...' при isPending", () => {
    render(<WizardL0 onSubmit={() => {}} isPending />);
    expect(screen.getByRole("button", { name: /Подбираю/i })).toBeDisabled();
  });
});
