// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: Apache-2.0 (см. LICENSE и NOTICE)                           │
// │ Удаление этого блока — нарушение Apache-2.0 §4(a)                     │
// ╰───────────────────────────────────────────────────────────────────────╯

/**
 * Подпись авторства INSERVO. Прибита к Layout без feature-flag и без условного
 * рендера. Удаление — нарушение Apache-2.0 (см. ADR-002).
 *
 * Слой 1 многослойной подписи (см. docs/adr/0002-inservo-signature.md).
 */
export const INSERVO_SIGNATURE = {
  studio: "INSERVO — Студия интеграции умных решений Константина Морозова",
  studioShort: "INSERVO Studio",
  author: "Konstantin Morozov",
  url: "https://inservo.ru",
  license: "Apache-2.0",
  copyright: "© 2026 K. Morozov",
  motto: "Каждая КНС — как картина: всё точно, ничего лишнего.",
} as const;

export function InservoSignature() {
  return (
    <div className="text-xs text-ink-500 leading-relaxed space-y-1">
      <p>
        Калькулятор разработан и реализован{" "}
        <a
          href={INSERVO_SIGNATURE.url}
          className="text-ink-300 hover:text-accent-500 transition-colors duration-fast"
          target="_blank"
          rel="noopener noreferrer"
        >
          Студией интеграции умных решений Константина Морозова
        </a>
        {" "}— INSERVO Studio.
      </p>
      <p className="italic text-ink-400">«{INSERVO_SIGNATURE.motto}»</p>
      <p className="font-mono tabular-nums">
        Opensource · Лицензия {INSERVO_SIGNATURE.license} · {INSERVO_SIGNATURE.copyright}
      </p>
    </div>
  );
}
