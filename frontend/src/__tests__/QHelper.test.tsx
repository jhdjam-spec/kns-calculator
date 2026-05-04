import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QHelper } from "@/components/QHelper";

describe("<QHelper>", () => {
  it("свёрнут по умолчанию", () => {
    render(<QHelper onCalculate={() => {}} />);
    expect(screen.getByText(/Не знаете расход в м³\/ч/i)).toBeInTheDocument();
    // Селект типа объекта не виден
    expect(screen.queryByText(/Тип объекта/i)).not.toBeInTheDocument();
  });

  it("раскрывается по клику", async () => {
    const user = userEvent.setup();
    render(<QHelper onCalculate={() => {}} />);
    await user.click(screen.getByText(/Не знаете расход в м³\/ч/i));
    expect(screen.getByText(/Тип объекта/i)).toBeInTheDocument();
  });

  it("гостиница 50 номеров → Q≈26 м³/ч (250 л/сут × 50 × 2.5 ÷ 24)", async () => {
    const user = userEvent.setup();
    const onCalc = vi.fn();
    render(<QHelper onCalculate={onCalc} />);

    await user.click(screen.getByText(/Не знаете расход в м³\/ч/i));
    // Выбираем тип "Гостиница / отель"
    const select = screen.getByRole("combobox");
    await user.selectOptions(select, "hotel");
    // Вводим 50 номеров
    const input = screen.getByPlaceholderText(/Введите число/i);
    await user.type(input, "50");

    // 250 × 50 / 1000 / 24 × 2.5 = 1.302 м³/ч (среднесут × Kgen)
    expect(screen.getByText(/1\.3\s*м³\/ч/)).toBeInTheDocument();

    // Жмём "Подставить в форму"
    await user.click(screen.getByText(/Подставить в форму расчёта/i));
    expect(onCalc).toHaveBeenCalledTimes(1);
    expect(onCalc.mock.calls[0][0]).toBeCloseTo(1.3, 1);
    expect(onCalc.mock.calls[0][1]).toMatch(/Гостиница.*50.*номеров/i);
  });

  it("частный дом 4 жителя → Q≈1.0 м³/ч (230 × 4 × 4.5 ÷ 24 / 1000)", async () => {
    const user = userEvent.setup();
    const onCalc = vi.fn();
    render(<QHelper onCalculate={onCalc} />);

    await user.click(screen.getByText(/Не знаете расход в м³\/ч/i));
    await user.selectOptions(screen.getByRole("combobox"), "private_house");
    await user.type(screen.getByPlaceholderText(/Введите число/i), "4");

    // 230 × 4 / 24000 × 4.5 = 0.172 м³/ч ≈ 0.2
    await user.click(screen.getByText(/Подставить в форму расчёта/i));
    expect(onCalc.mock.calls[0][0]).toBeCloseTo(0.2, 1);
  });

  it("не показывает кнопку подстановки при пустом или 0", async () => {
    const user = userEvent.setup();
    const onCalc = vi.fn();
    render(<QHelper onCalculate={onCalc} />);
    await user.click(screen.getByText(/Не знаете расход в м³\/ч/i));
    // Кнопки подстановки нет, пока ничего не введено
    expect(screen.queryByText(/Подставить в форму расчёта/i)).not.toBeInTheDocument();
  });
});
