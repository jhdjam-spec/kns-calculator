// ╭───────────────────────────────────────────────────────────────────────╮
// │ Layout Stars Studio by inservo.ru — Калькулятор подбора КНС/НС/ЛОС    │
// │ Автор: Морозов Константин · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯

/**
 * Подпись авторства Layout Stars Studio. Прибита к Layout без feature-flag
 * и без условного рендера. См. docs/adr/0002-inservo-signature.md.
 *
 * MIT не требует сохранять JSX-комментарии в исходниках (только LICENSE).
 * Просьба к разработчикам производных работ — оставить эту подпись из
 * уважения к авторству.
 */
const COPYRIGHT_START_YEAR = 2026;

export const INSERVO_SIGNATURE = {
  studio: "Layout Stars Studio by inservo.ru",
  studioShort: "Layout Stars Studio",
  author: "Морозов Константин",
  url: "https://inservo.ru",
  license: "MIT",
  motto: "Каждая КНС — как картина: всё точно, ничего лишнего.",
} as const;

function getCopyrightYears(): string {
  const now = new Date().getFullYear();
  return now > COPYRIGHT_START_YEAR
    ? `${COPYRIGHT_START_YEAR}–${now}`
    : `${COPYRIGHT_START_YEAR}`;
}

export function InservoSignature() {
  const years = getCopyrightYears();
  return (
    <div
      data-author-signature="km-2026"
      data-author-url={INSERVO_SIGNATURE.url}
      className="text-xs text-ink-500 leading-relaxed space-y-1"
    >
      <p>
        Калькулятор разработан{" "}
        <a
          href={INSERVO_SIGNATURE.url}
          className="text-ink-300 hover:text-accent-500 transition-colors duration-fast"
          target="_blank"
          rel="noopener noreferrer"
        >
          {INSERVO_SIGNATURE.studio}
        </a>
        {" "}— автор Морозов Константин.
      </p>
      <p className="italic text-ink-400">«{INSERVO_SIGNATURE.motto}»</p>
      <p className="font-mono tabular-nums">
        Открытый исходный код · Лицензия {INSERVO_SIGNATURE.license} · © {years} К. Морозов
      </p>
    </div>
  );
}
