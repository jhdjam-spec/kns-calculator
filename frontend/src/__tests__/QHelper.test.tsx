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

  it("ЖК на 1000 квартир → Q ≈ 58 м³/ч (700 × 1000 × 2.0 ÷ 24 / 1000)", async () => {
    const user = userEvent.setup();
    const onCalc = vi.fn();
    render(<QHelper onCalculate={onCalc} />);

    await user.click(screen.getByText(/Не знаете расход в м³\/ч/i));
    const select = screen.getByLabelText(/Тип объекта/i);
    await user.selectOptions(select, "housing_complex");
    await user.type(screen.getByPlaceholderText(/Введите число/i), "1000");

    // 700 × 1000 / 1000 / 24 × 2.0 = 58.33 ≈ 58.3
    await user.click(screen.getByText(/Подставить в форму расчёта/i));
    expect(onCalc.mock.calls[0][0]).toBeCloseTo(58.3, 1);
    expect(onCalc.mock.calls[0][1]).toMatch(/Жилой комплекс.*1000.*квартир/i);
  });

  it("аэропорт 100 000 пассажиров/день → Q ≈ 67 м³/ч", async () => {
    const user = userEvent.setup();
    const onCalc = vi.fn();
    render(<QHelper onCalculate={onCalc} />);

    await user.click(screen.getByText(/Не знаете расход в м³\/ч/i));
    await user.selectOptions(screen.getByLabelText(/Тип объекта/i), "airport_station");
    await user.type(screen.getByPlaceholderText(/Введите число/i), "100000");

    // 8 × 100000 / 1000 / 24 × 2.0 = 66.67 ≈ 66.7
    await user.click(screen.getByText(/Подставить в форму расчёта/i));
    expect(onCalc.mock.calls[0][0]).toBeCloseTo(66.7, 1);
  });

  describe("Дождевая канализация (drainage)", () => {
    it("переключает режим по клику на вкладку", async () => {
      const user = userEvent.setup();
      render(<QHelper onCalculate={() => {}} />);
      await user.click(screen.getByText(/Не знаете расход в м³\/ч/i));
      // По умолчанию domestic — виден селект «Тип объекта»
      expect(screen.getByLabelText(/Тип объекта/i)).toBeInTheDocument();
      // Переключаем на drainage
      await user.click(screen.getByRole("tab", { name: /Дождевая канализация/i }));
      // Теперь виден селект «Регион»
      expect(screen.getByLabelText(/Регион/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Тип поверхности/i)).toBeInTheDocument();
    });

    it("Уташ-кейс: 5 га асфальта на юге РФ → Q ≈ 1153 м³/ч", async () => {
      const user = userEvent.setup();
      const onCalc = vi.fn();
      render(<QHelper onCalculate={onCalc} />);
      await user.click(screen.getByText(/Не знаете расход в м³\/ч/i));
      await user.click(screen.getByRole("tab", { name: /Дождевая канализация/i }));

      await user.selectOptions(screen.getByLabelText(/Регион/i), "south_krd");
      await user.selectOptions(screen.getByLabelText(/Тип поверхности/i), "asphalt");
      await user.type(screen.getByPlaceholderText(/Например, 50000/i), "50000");

      // F = 5 га, ψ = 0.95, q20 = 90, β = 0.75 → Q_ls = 320.625 → Q_m3h = 1154.25
      await user.click(screen.getByText(/Подставить в форму расчёта/i));
      expect(onCalc.mock.calls[0][0]).toBeCloseTo(1154.3, 0);
      expect(onCalc.mock.calls[0][1]).toMatch(/Дождевая.*50.*000.*м²/i);
    });

    it("газон 1 га в Москве → Q ≈ 22 м³/ч (низкий ψ)", async () => {
      const user = userEvent.setup();
      const onCalc = vi.fn();
      render(<QHelper onCalculate={onCalc} />);
      await user.click(screen.getByText(/Не знаете расход в м³\/ч/i));
      await user.click(screen.getByRole("tab", { name: /Дождевая канализация/i }));

      await user.selectOptions(screen.getByLabelText(/Регион/i), "moscow");
      await user.selectOptions(screen.getByLabelText(/Тип поверхности/i), "lawn");
      await user.type(screen.getByPlaceholderText(/Например, 50000/i), "10000");

      // F = 1 га, ψ = 0.10, q20 = 80, β = 0.75 → Q_ls = 6 → Q_m3h = 21.6
      await user.click(screen.getByText(/Подставить в форму расчёта/i));
      expect(onCalc.mock.calls[0][0]).toBeCloseTo(21.6, 1);
    });
  });
});
