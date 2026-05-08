// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { InservoSignature, INSERVO_SIGNATURE } from "@/components/InservoSignature";
import { BetaBanner } from "@/components/BetaBanner";

/**
 * Тесты на присутствие подписи авторства INSERVO в DOM.
 *
 * Цель: реализация Слоя 5 ADR-002 (docs/adr/0002-inservo-signature.md) —
 * скрытая подпись на уровне тестов. Если кто-то форкнёт проект и удалит
 * компоненты подписи ради чистки — `npm test` упадёт. Чинить = либо
 * вернуть подпись, либо удалить тест (явное действие, фиксируется в
 * git-истории форка).
 *
 * MIT не запрещает удалять эти тесты или подпись — это просьба автора.
 */
describe("INSERVO Signature presence", () => {
  it("InservoSignature рендерит data-атрибут авторства", () => {
    const { container } = render(<InservoSignature />);
    const signatureEl = container.querySelector("[data-inservo-signature]");
    expect(signatureEl).not.toBeNull();
    expect(signatureEl?.getAttribute("data-inservo-signature")).toBe("km-2026");
    expect(signatureEl?.getAttribute("data-inservo-url")).toBe("https://inservo.ru");
  });

  it("InservoSignature содержит имя студии и автора", () => {
    const { container } = render(<InservoSignature />);
    const text = container.textContent ?? "";
    expect(text).toContain("Константина Морозова");
    expect(text).toContain("INSERVO");
    expect(text).toContain("Apache".replace("Apache", "MIT")); // лицензия должна быть MIT
    expect(text).toContain("MIT");
  });

  it("InservoSignature содержит девиз-подпись художника", () => {
    const { container } = render(<InservoSignature />);
    expect(container.textContent).toContain("Каждая КНС");
  });

  it("Год copyright обновляется автоматически (не захардкожен)", () => {
    const { container } = render(<InservoSignature />);
    const currentYear = new Date().getFullYear();
    expect(container.textContent).toContain(String(currentYear));
  });

  it("Константа INSERVO_SIGNATURE экспортируется и содержит ключевые поля", () => {
    expect(INSERVO_SIGNATURE.url).toBe("https://inservo.ru");
    expect(INSERVO_SIGNATURE.license).toBe("MIT");
    expect(INSERVO_SIGNATURE.author).toBe("Konstantin Morozov");
    expect(INSERVO_SIGNATURE.studioShort).toBe("INSERVO Studio");
  });

  it("Ссылка на inservo.ru открывается в новой вкладке с rel=noopener", () => {
    const { container } = render(<InservoSignature />);
    const link = container.querySelector('a[href="https://inservo.ru"]');
    expect(link).not.toBeNull();
    expect(link?.getAttribute("target")).toBe("_blank");
    expect(link?.getAttribute("rel")).toContain("noopener");
  });
});

describe("BetaBanner — защита от использования бета-результатов", () => {
  it("Рендерится с role=status (не alert — иначе скринридер прерывает навигацию)", () => {
    const { container } = render(<BetaBanner />);
    const banner = container.querySelector('[role="status"]');
    expect(banner).not.toBeNull();
    // role="alert" недопустим для статичного баннера — должен быть status
    const alert = container.querySelector('[role="alert"]');
    expect(alert).toBeNull();
  });

  it("Содержит слово «Бета» и упоминание инженера", () => {
    const { container } = render(<BetaBanner />);
    const text = container.textContent ?? "";
    expect(text).toContain("Бета");
    expect(text.toLowerCase()).toContain("инженер");
  });
});
