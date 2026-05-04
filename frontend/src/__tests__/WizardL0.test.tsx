import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WizardL0 } from "@/components/WizardL0";

describe("<WizardL0>", () => {
  it("рендерит 4 поля и кнопку", () => {
    render(<WizardL0 onSubmit={() => {}} />);

    // Поле расхода ищем по id (label "Расход" есть и у группы — не уникален)
    expect(document.getElementById("Q_value")).toBeInTheDocument();
    expect(screen.getByLabelText(/Перепад высот/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Длина напорной трассы/i)).toBeInTheDocument();
    expect(screen.getByText(/Тип стоков/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Подобрать насос/i })).toBeInTheDocument();
  });

  it("при сабмите формы с явно выбранным типом стоков отправляет все 4 поля", async () => {
    const user = userEvent.setup();
    const handle = vi.fn();
    render(<WizardL0 onSubmit={handle} />);

    await user.type(document.getElementById("Q_value")!, "21.2");
    await user.type(screen.getByLabelText(/Перепад высот/i), "10");
    await user.type(screen.getByLabelText(/Длина напорной трассы/i), "0");
    // Выбираем radio domestic явно (есть несколько вариантов с именем «Хоз-бытовые»)
    const radios = screen.getAllByRole("radio");
    const domesticRadio = radios.find(
      (r) => (r as HTMLInputElement).value === "domestic"
    )!;
    await user.click(domesticRadio);
    await user.click(screen.getByRole("button", { name: /Подобрать насос/i }));

    await waitFor(() => {
      expect(handle).toHaveBeenCalledTimes(1);
    });
    // Контракт onSubmit: SelectionRequest = { L0, L1? }
    expect(handle.mock.calls[0][0]).toEqual({
      L0: {
        Q_m3h: 21.2,
        dH_m: 10,
        L_m: 0,
        wastewater_type: "domestic",
      },
      // L1 не отправляется при corpus_material="pe" (default)
    });
  });

  it("сабмит с одним только Q отправляет минимальный L0Input (опциональные поля backend подставит)", async () => {
    const user = userEvent.setup();
    const handle = vi.fn();
    render(<WizardL0 onSubmit={handle} />);

    await user.type(document.getElementById("Q_value")!, "21.2");
    // dH, L, wastewater_type — оставляем по умолчанию (пустые)
    await user.click(screen.getByRole("button", { name: /Подобрать насос/i }));

    await waitFor(() => expect(handle).toHaveBeenCalledTimes(1));
    const req = handle.mock.calls[0][0];
    expect(req.L0.Q_m3h).toBe(21.2);
    expect(req.L0.dH_m).toBeUndefined();
    expect(req.L0.L_m).toBeUndefined();
    expect(req.L0.wastewater_type).toBeUndefined();
    // PE (default) — L1 не отправляется
    expect(req.L1).toBeUndefined();
  });

  it("сабмит с corpus_material=glass отправляет L1.corpus_material", async () => {
    const user = userEvent.setup();
    const handle = vi.fn();
    render(<WizardL0 onSubmit={handle} />);

    await user.type(document.getElementById("Q_value")!, "21.2");
    // Выбираем стеклопластик
    const radios = screen.getAllByRole("radio");
    const glassRadio = radios.find(
      (r) => (r as HTMLInputElement).value === "glass"
    )!;
    await user.click(glassRadio);
    await user.click(screen.getByRole("button", { name: /Подобрать насос/i }));

    await waitFor(() => expect(handle).toHaveBeenCalledTimes(1));
    const req = handle.mock.calls[0][0];
    expect(req.L1).toEqual({ corpus_material: "glass" });
  });

  it("блокирует сабмит при пустом Q (Q обязательный)", async () => {
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
    await user.type(screen.getByLabelText(/Перепад высот/i), "10");
    await user.type(screen.getByLabelText(/Длина напорной трассы/i), "0");
    await user.click(screen.getByRole("button", { name: /Подобрать насос/i }));

    await waitFor(() => expect(handle).toHaveBeenCalled());
    const req = handle.mock.calls[0][0];
    expect(req.L0.Q_m3h).toBeCloseTo(21.24, 2);
  });

  it("отображает 'Подбираю...' при isPending", () => {
    render(<WizardL0 onSubmit={() => {}} isPending />);
    expect(screen.getByRole("button", { name: /Подбираю/i })).toBeDisabled();
  });
});
