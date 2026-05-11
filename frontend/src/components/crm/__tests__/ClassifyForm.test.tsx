import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ClassifyForm, type ClassifyResponse } from "@/components/crm/ClassifyForm";

const SAMPLE_RESPONSE: ClassifyResponse = {
  type: "ОЛ",
  object: "КНС",
  manufacturer: "GRUNDFOS",
  project_codes: ["2799289", "БСВП0001809"],
  is_trusted_sender: true,
};

function makeFetchMock(response: ClassifyResponse, ok = true, status = 200) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    statusText: ok ? "OK" : "Bad Request",
    json: async () => response,
    text: async () => JSON.stringify(response),
  } as Response);
}

describe("<ClassifyForm>", () => {
  it("рендерит поля ввода и кнопку «Распознать»", () => {
    render(<ClassifyForm />);
    expect(screen.getByLabelText("Тема письма")).toBeInTheDocument();
    expect(screen.getByLabelText("Тело письма")).toBeInTheDocument();
    expect(screen.getByLabelText("Email отправителя")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Распознать/i }),
    ).toBeInTheDocument();
  });

  it("при пустых полях кнопка «Распознать» disabled", () => {
    render(<ClassifyForm />);
    const btn = screen.getByRole("button", { name: /Распознать/i });
    expect(btn).toBeDisabled();
  });

  it("отправляет запрос и рендерит результат с бейджами", async () => {
    const fetchMock = makeFetchMock(SAMPLE_RESPONSE);
    render(<ClassifyForm fetchImpl={fetchMock as unknown as typeof fetch} />);

    fireEvent.change(screen.getByLabelText("Тема письма"), {
      target: { value: "ОЛ на КНС-2" },
    });
    fireEvent.change(screen.getByLabelText("Тело письма"), {
      target: { value: "Шифр 2799289, нужно КП" },
    });
    fireEvent.change(screen.getByLabelText("Email отправителя"), {
      target: { value: "zakaz@inservo.ru" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Распознать/i }));

    await waitFor(() => {
      expect(screen.getByTestId("classify-result")).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/etl\/classify$/);
    expect(opts.method).toBe("POST");
    const sentBody = JSON.parse(opts.body as string);
    expect(sentBody.subject).toBe("ОЛ на КНС-2");
    expect(sentBody.from_email).toBe("zakaz@inservo.ru");

    expect(screen.getByTestId("result-type")).toHaveTextContent("ОЛ");
    expect(screen.getByTestId("result-object")).toHaveTextContent("КНС");
    expect(screen.getByTestId("result-manufacturer")).toHaveTextContent(
      "GRUNDFOS",
    );
    const codes = screen.getByTestId("project-codes");
    expect(codes).toHaveTextContent("2799289");
    expect(codes).toHaveTextContent("БСВП0001809");
    expect(screen.getByTestId("trusted-indicator")).toBeInTheDocument();
  });

  it("показывает untrusted-indicator при is_trusted_sender=false", async () => {
    const fetchMock = makeFetchMock({
      ...SAMPLE_RESPONSE,
      is_trusted_sender: false,
    });
    render(<ClassifyForm fetchImpl={fetchMock as unknown as typeof fetch} />);
    fireEvent.change(screen.getByLabelText("Тема письма"), {
      target: { value: "Что-то" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Распознать/i }));
    await waitFor(() => {
      expect(screen.getByTestId("untrusted-indicator")).toBeInTheDocument();
    });
  });

  it("показывает ошибку при !response.ok", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: async () => ({ detail: "empty" }),
      text: async () => "Все поля пусты",
    } as Response);
    render(<ClassifyForm fetchImpl={fetchMock as unknown as typeof fetch} />);
    fireEvent.change(screen.getByLabelText("Тема письма"), {
      target: { value: "x" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Распознать/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(screen.getByRole("alert")).toHaveTextContent(/HTTP 400/);
  });
});
