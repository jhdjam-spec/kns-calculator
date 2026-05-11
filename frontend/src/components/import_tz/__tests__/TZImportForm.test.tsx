import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { TZImportForm, type TZParseResponse } from "@/components/import_tz/TZImportForm";

const SAMPLE_RESPONSE: TZParseResponse = {
  Q_m3h: 88.6,
  dH_m: 39,
  city: "Краснодар",
  wastewater_type: "domestic",
  project_code: "1578-22-НК",
  project_codes: ["1578-22-НК"],
  object_type: "КНС",
  manufacturer: null,
  Ex_required: false,
  reliability: null,
  liquid_temp_c: null,
  extracted_text_chars: 180,
  confidence: 1.0,
  fields_found: ["Q", "H", "city", "wastewater_type"],
  raw_matches: {},
  archive_path: null,
  archive_error: null,
  archive_size_bytes: 0,
};

function makeFetchMock(response: TZParseResponse, ok = true, status = 200) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    statusText: ok ? "OK" : "Bad Request",
    json: async () => response,
    text: async () => JSON.stringify(response),
  } as Response);
}

describe("<TZImportForm>", () => {
  it("рендерит textarea и кнопку «Распознать»", () => {
    render(<TZImportForm />);
    expect(screen.getByTestId("tz-textarea")).toBeInTheDocument();
    expect(screen.getByTestId("tz-parse-btn")).toBeInTheDocument();
  });

  it("при пустом тексте кнопка «Распознать» disabled", () => {
    render(<TZImportForm />);
    const btn = screen.getByTestId("tz-parse-btn");
    expect(btn).toBeDisabled();
  });

  it("отправляет POST /import/parse и рендерит извлечённые поля", async () => {
    const fetchMock = makeFetchMock(SAMPLE_RESPONSE);
    render(<TZImportForm fetchImpl={fetchMock as unknown as typeof fetch} />);

    fireEvent.change(screen.getByTestId("tz-textarea"), {
      target: {
        value:
          "Тех.задание на КНС. Q=88.6 м³/ч, напор 39 м, г. Краснодар, бытовые, шифр 1578-22-НК",
      },
    });
    fireEvent.click(screen.getByTestId("tz-parse-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("tz-result")).toBeInTheDocument();
    });

    // Поля извлечены
    expect(screen.getByTestId("tz-q")).toHaveTextContent("88.6 м³/ч");
    expect(screen.getByTestId("tz-h")).toHaveTextContent("39 м");
    expect(screen.getByTestId("tz-city")).toHaveTextContent("Краснодар");
    expect(screen.getByTestId("tz-wastewater")).toHaveTextContent("бытовые");
    expect(screen.getByTestId("tz-code")).toHaveTextContent("1578-22-НК");

    // Confidence 100%
    expect(screen.getByTestId("tz-confidence")).toHaveTextContent("100%");

    // CTA-кнопки содержат правильные URL
    const projectCta = screen.getByTestId("tz-cta-project") as HTMLAnchorElement;
    expect(projectCta.href).toContain("/project");
    expect(projectCta.href).toContain("q=88.6");
    expect(projectCta.href).toContain("dh=39");
    expect(projectCta.href).toContain("preset=auto");

    const quickCta = screen.getByTestId("tz-cta-quick") as HTMLAnchorElement;
    expect(quickCta.href).toContain("calculator");
    expect(quickCta.href).toContain("q=88.6");
  });

  it("показывает ошибку на 400 от backend", async () => {
    const fetchMock = makeFetchMock(SAMPLE_RESPONSE, false, 400);
    render(<TZImportForm fetchImpl={fetchMock as unknown as typeof fetch} />);
    fireEvent.change(screen.getByTestId("tz-textarea"), {
      target: { value: "что-то" },
    });
    fireEvent.click(screen.getByTestId("tz-parse-btn"));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  it("кнопка «Очистить» очищает textarea", () => {
    render(<TZImportForm />);
    const ta = screen.getByTestId("tz-textarea") as HTMLTextAreaElement;
    fireEvent.change(ta, { target: { value: "Q=20 м³/ч" } });
    expect(ta.value).toBe("Q=20 м³/ч");
    fireEvent.click(screen.getByRole("button", { name: /Очистить/i }));
    expect(ta.value).toBe("");
  });

  it("archive_path и archive_error СКРЫТЫ от пользователя (служебная функция)", async () => {
    // По требованию заказчика — backend сохраняет в Я.Диск/S3 для dataset
    // enrichment, но UI НЕ должен показывать факт сохранения пользователю.
    const withArchive: TZParseResponse = {
      ...SAMPLE_RESPONSE,
      archive_path: "/inservo_tz_archive/2026-05-11/test.txt",
      archive_error: null,
      archive_size_bytes: 1024,
    };
    const fetchMock = makeFetchMock(withArchive);
    render(<TZImportForm fetchImpl={fetchMock as unknown as typeof fetch} />);
    fireEvent.change(screen.getByTestId("tz-textarea"), {
      target: { value: "Q=88.6 м³/ч" },
    });
    fireEvent.click(screen.getByTestId("tz-parse-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("tz-q")).toBeInTheDocument();
    });
    // Archive UI блоки НЕ должны быть в DOM
    expect(screen.queryByTestId("tz-archive-ok")).not.toBeInTheDocument();
    expect(screen.queryByTestId("tz-archive-path")).not.toBeInTheDocument();
    expect(screen.queryByTestId("tz-archive-warn")).not.toBeInTheDocument();
    expect(screen.queryByText(/Сохранено в архив/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/inservo_tz_archive/i)).not.toBeInTheDocument();
  });

  it("file-upload .txt заполняет textarea и сохраняет original_filename", async () => {
    const fetchMock = makeFetchMock(SAMPLE_RESPONSE);
    render(<TZImportForm fetchImpl={fetchMock as unknown as typeof fetch} />);

    const file = new File(
      ["Q=88.6 м³/ч, напор 39 м, г. Краснодар"],
      "техзадание.txt",
      { type: "text/plain" },
    );
    const input = screen.getByTestId("tz-file-input") as HTMLInputElement;
    Object.defineProperty(input, "files", {
      value: [file],
      configurable: true,
    });
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByTestId("tz-original-filename")).toHaveTextContent(
        "техзадание.txt",
      );
    });
    const ta = screen.getByTestId("tz-textarea") as HTMLTextAreaElement;
    await waitFor(() => {
      expect(ta.value).toContain("88.6");
    });

    // Клик «Распознать» — body содержит original_filename
    fireEvent.click(screen.getByTestId("tz-parse-btn"));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });
    const callArgs = fetchMock.mock.calls[0];
    const sentBody = JSON.parse((callArgs[1] as RequestInit).body as string);
    expect(sentBody.original_filename).toBe("техзадание.txt");
  });

  it("частичное извлечение (только Q) показывает amber confidence", async () => {
    const partial: TZParseResponse = {
      ...SAMPLE_RESPONSE,
      dH_m: null,
      city: null,
      wastewater_type: null,
      project_code: null,
      project_codes: [],
      object_type: null,
      confidence: 0.25,
      fields_found: ["Q"],
    };
    const fetchMock = makeFetchMock(partial);
    render(<TZImportForm fetchImpl={fetchMock as unknown as typeof fetch} />);
    fireEvent.change(screen.getByTestId("tz-textarea"), {
      target: { value: "Q=20 м³/ч" },
    });
    fireEvent.click(screen.getByTestId("tz-parse-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("tz-confidence")).toHaveTextContent("25%");
    });
    expect(screen.getByTestId("tz-h")).toHaveTextContent("не извлечено");
    expect(screen.getByTestId("tz-city")).toHaveTextContent("не извлечено");
  });
});
