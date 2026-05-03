"""Извлечение списка моделей насосов (RawPumpDraft) из таблиц DocumentChunk.

Модуль работает с уже извлечёнными таблицами (см. docling_runner / pdfplumber_runner)
и собирает по ним «черновики» паспортных записей насосов. Q-H кривая на этом этапе
НЕ заполняется — её собирает отдельный модуль `qh_extractor` (этап 6.3). Сшивка
drafts + Q-H точек происходит в `pipeline.py` (этап 6.4) и даёт итоговый
`RawPumpRecord`, который уже умеет принимать существующий `importer.py`.

Подход:
    1. Сканируем все таблицы из chunks.
    2. Находим «model anchor» таблицы — те, в первой колонке которых встречаются
       имена моделей вида ``VXm 8/35`` или ``VX 20/50`` (см. ``MODEL_NAME_RE``).
       В каталоге Pedrollo VX это таблицы со спецификацией моделей под графиками
       Q-H: одна строка содержит обе фазности (``VXm 8/35`` и ``VX 8/35``) и
       номинальную мощность P2 в кВт.
    3. Находим таблицы с PORT (DN) и Passage of solid bodies — таблица
       присоединительных размеров. Здесь значения объединены ячейками PDF, поэтому
       для пустых строк наследуем последнее не-пустое значение в той же серии
       (логика «merged cell forward fill»).
    4. Сшиваем по имени модели (без префикса ``m`` для VXm, чтобы найти данные
       в DN-таблице, где перечислены только VX) → получаем
       ``free_passage_mm`` и ``discharge_DN_mm`` для каждой модели.
    5. Получаем 16 драфтов: 8 single-phase VXm (230 В) + 8 three-phase VX (400 В).

LLM-режим (``use_llm=True``) опционален и требует ANTHROPIC_API_KEY в окружении.
По умолчанию rule-based — для Pedrollo VX этого достаточно.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable

from pydantic import BaseModel, Field, PrivateAttr

from pump_calculator.etl.pdf.docling_runner import DocumentChunk

# ----------- Regex constants -----------------------------------------------

# Имя модели Pedrollo VX: ``VX 8/35``, ``VXm 10/50``, ``VX20/35`` (со слитным
# написанием и с пробелом). Допускаем как один пробел, так и его отсутствие.
MODEL_NAME_RE = re.compile(r"^V[Xx](?P<phase>m?)\s*(?P<size>\d+/\d+)$")

# Распознавание DN из строки вроде "1¼\" / Ø 40 mm" или "2\""
DN_INCH_TO_MM = {
    "1": 25.0,
    "1¼": 32.0,
    "1¼\"": 32.0,
    "1½": 40.0,
    "1½\"": 40.0,
    "2": 50.0,
    "2\"": 50.0,
    "2½": 65.0,
    "3": 80.0,
    "4": 100.0,
}

# Из строки вроде "Ø 40 mm" или "Ø50mm" вынимаем число.
PASSAGE_MM_RE = re.compile(r"Ø?\s*(?P<mm>\d+(?:\.\d+)?)\s*mm", re.IGNORECASE)

# Минимум сколько имён моделей должно встретиться в таблице, чтобы счесть её
# anchor-таблицей моделей.
MIN_MODELS_PER_ANCHOR = 2


# ----------- Pydantic-модели -----------------------------------------------


class RawPumpDraft(BaseModel):
    """Промежуточный draft `RawPumpRecord` без поля ``qh_curve``.

    `qh_curve` будет заполнен отдельно `qh_extractor` (этап 6.3). После сшивки
    drafts + curves в `pipeline.py` получаем полноценный `RawPumpRecord`.

    Поля повторяют контракт `RawPumpRecord`, но без обязательных Q-H точек,
    чтобы можно было собрать draft до запуска оцифровки графиков.
    """

    brand: str
    model: str = Field(..., description="Точное имя из паспорта, например 'VX 8/35'")
    type: str = "submersible_sewage"
    impeller: str | None = None
    free_passage_mm: float = Field(..., ge=0, le=200)
    P_kW: float = Field(..., gt=0)
    voltage_v: int = 380  # 230 для VXm, 380 для VX
    phase: int = 3  # 1 для VXm, 3 для VX
    ip_rating: str = "IP68"
    discharge_DN_mm: float | None = None
    wastewater_compat: list[str] = Field(
        default_factory=lambda: ["domestic", "drainage", "industrial"]
    )
    price_segment: str = "premium"  # Pedrollo — премиум-сегмент
    available_ru_status: str = "official"
    distributor: str | None = "Pedrollo Россия (pedrollo.ru)"
    warranty_months: int = 24
    notes: str | None = None

    # ----- Метаданные источника (приватные, не попадают в RawPumpRecord) -----
    _source_pages: list[int] = PrivateAttr(default_factory=list)


# ----------- Helpers --------------------------------------------------------


def _iter_table_cells(table: dict) -> Iterable[str]:
    """Перебрать все ячейки таблицы (header + df) как нормализованные строки."""
    for cell in table.get("header", []) or []:
        yield (cell or "").strip()
    for row in table.get("df", []) or []:
        for cell in row or []:
            yield (cell or "").strip()


def _normalize_model_name(raw: str) -> str | None:
    """Привести 'VXm 8/35', 'VX10/50', 'VX 8 /35' → каноническое 'VXm 8/35' / 'VX 8/35'.

    Возвращает None если строка не похожа на имя модели Pedrollo VX.
    """
    text = re.sub(r"\s+", " ", raw.strip())
    # Допускаем "VXm8/35" (без пробела), нормализуем в "VXm 8/35"
    text = re.sub(r"^(V[Xx]m?)(\d)", r"\1 \2", text)
    text = re.sub(r"\s*/\s*", "/", text)  # 'VX 8 / 35' → 'VX 8/35'
    m = MODEL_NAME_RE.match(text)
    if not m:
        return None
    phase = "m" if m.group("phase").lower() == "m" else ""
    return f"VX{phase} {m.group('size')}"


def _row_first_cell_model(row: list[str]) -> str | None:
    """Вернуть нормализованное имя модели из первой непустой ячейки строки.

    Pedrollo VX иногда «склеивает» имя в первой ячейке, но также часто
    разбивает его на 2-3 соседних ячеек (``['VX2', '0/', '35']``). В этой
    функции мы рассматриваем именно первую непустую цельную ячейку — это
    надёжный маркер anchor-строки в таблицах со спецификацией.
    """
    for cell in row:
        cell = (cell or "").strip()
        if not cell:
            continue
        return _normalize_model_name(cell)
    return None


def _is_model_anchor_table(table: dict) -> bool:
    """Таблица — anchor моделей, если в первой колонке встречается ≥2 имён моделей."""
    found = 0
    for row in table.get("df", []) or []:
        if _row_first_cell_model(row or []):
            found += 1
            if found >= MIN_MODELS_PER_ANCHOR:
                return True
    return False


def _parse_kw(text: str) -> float | None:
    """'0.55' → 0.55; '1,5' → 1.5; '' → None."""
    text = (text or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_dn(text: str) -> float | None:
    """'1½\"' → 40, '2\"' → 50, '40 mm' → 40, '' → None."""
    text = (text or "").strip()
    if not text:
        return None
    # Сначала пробуем «миллиметровую» форму
    m = PASSAGE_MM_RE.search(text)
    if m:
        return float(m.group("mm"))
    # Попытка по словарю дюймов: убираем хвостовое 'NPT', 'BSP', пробелы
    inch_token = text.split()[0]
    if inch_token in DN_INCH_TO_MM:
        return DN_INCH_TO_MM[inch_token]
    return None


def _parse_passage_mm(text: str) -> float | None:
    """'Ø 40 mm' → 40.0, '40' → 40.0, '' → None."""
    text = (text or "").strip()
    if not text:
        return None
    m = PASSAGE_MM_RE.search(text)
    if m:
        return float(m.group("mm"))
    # Голое число
    try:
        return float(text)
    except ValueError:
        return None


def _extract_anchor_rows(
    table: dict,
) -> list[tuple[str, float | None, list[str]]]:
    """Достать из anchor-таблицы тройки (имя_модели, power_kW, оригинальная_строка).

    В Pedrollo VX строка спецификации выглядит так:
        ['VXm 8/35', 'VX 8/35', '0.55', '0.75', 'H metres', '', '9', '8', ...]

    Здесь:
        col 0 — single-phase model (VXm)
        col 1 — three-phase model (VX)
        col 2 — P2 в kW (общий для обеих фазностей)
        col 3 — P2 в HP
        col >=6 — Q-H значения (используются на этапе 6.3)

    Мы возвращаем по два элемента на строку: один для VXm, один для VX,
    с одной и той же мощностью.
    """
    rows: list[tuple[str, float | None, list[str]]] = []
    for raw_row in table.get("df", []) or []:
        if not raw_row:
            continue
        # Ищем все имена моделей в первых двух колонках
        names: list[str] = []
        for cell in raw_row[:2]:
            name = _normalize_model_name((cell or "").strip())
            if name:
                names.append(name)
        if not names:
            continue
        # Мощность — третья колонка (P2 kW). Иногда она в 4-й, ищем первую распарсенную.
        power_kw: float | None = None
        for cell in raw_row[2:5]:
            power_kw = _parse_kw(cell)
            if power_kw is not None:
                break
        for name in names:
            rows.append((name, power_kw, list(raw_row)))
    return rows


def _extract_dn_passage_table(
    table: dict,
) -> dict[str, tuple[float | None, float | None]]:
    """Из таблицы PORT/Passage достать ``{model_size: (DN_mm, passage_mm)}``.

    Pedrollo VX merge-ячеек: значение указано в первой строке серии (например,
    ``VX 8/35``), а для последующих VX 10/35, VX 15/35, VX 20/35 ячейки пустые.
    Реализуем forward-fill: пустое значение наследуется от последнего видимого.

    Ключи словаря — нормализованное имя без префикса 'm', чтобы это работало
    для обеих фазностей: для VXm 8/35 lookup идёт по 'VX 8/35'.
    """
    out: dict[str, tuple[float | None, float | None]] = {}
    last_dn: float | None = None
    last_passage: float | None = None
    for raw_row in table.get("df", []) or []:
        if not raw_row:
            continue
        first = (raw_row[0] or "").strip()
        name = _normalize_model_name(first)
        if not name:
            continue
        # Колонки 1 и 2: PORT DN, Passage of solid bodies
        dn_text = raw_row[1] if len(raw_row) > 1 else ""
        passage_text = raw_row[2] if len(raw_row) > 2 else ""
        dn = _parse_dn(dn_text) or last_dn
        passage = _parse_passage_mm(passage_text) or last_passage
        if dn is not None:
            last_dn = dn
        if passage is not None:
            last_passage = passage
        # Сохраняем по three-phase ключу (без 'm'), чтобы матчить обе фазности.
        key = name if not name.startswith("VXm") else "VX " + name.split(" ", 1)[1]
        out[key] = (dn, passage)
    return out


def _is_dn_passage_table(table: dict) -> bool:
    """Эвристика: таблица содержит DN и Passage в заголовке или модель + DN-данные."""
    header_text = " ".join((c or "") for c in table.get("header", []) or []).lower()
    if "port" in header_text and ("passage" in header_text or "dn" in header_text):
        return True
    # Fallback: ищем по содержимому строк
    has_model = False
    has_dn_or_passage = False
    for cell in _iter_table_cells(table):
        if _normalize_model_name(cell):
            has_model = True
        if PASSAGE_MM_RE.search(cell) or cell.strip() in DN_INCH_TO_MM:
            has_dn_or_passage = True
    return has_model and has_dn_or_passage


# ----------- Public API -----------------------------------------------------


def extract_pumps_from_chunks(
    chunks: list[DocumentChunk],
    brand_hint: str = "Pedrollo",
    use_llm: bool = False,
) -> list[RawPumpDraft]:
    """Извлечь список черновиков насосов из набора DocumentChunk.

    Алгоритм описан в docstring модуля.

    Args:
        chunks:     результат прогона `pdfplumber_runner.run_pdfplumber` или
                    `docling_runner.run_docling`. Используем поле ``.tables``.
        brand_hint: бренд для проставления в каждый draft (по умолчанию ``Pedrollo``).
        use_llm:    если True — вместо rule-based используется Pydantic-AI агент
                    на ``claude-haiku-4-5-20251001``. Требует ``ANTHROPIC_API_KEY``.
                    По умолчанию False — rule-based parser отлично справляется
                    с Pedrollo VX и не зависит от внешних API.

    Returns:
        Список ``RawPumpDraft``, каждый соответствует одной модели каталога.
        Для Pedrollo VX 50 Hz это 16 элементов (8 пар single/three-phase).

    Raises:
        RuntimeError: если ``use_llm=True``, но ``ANTHROPIC_API_KEY`` не задан.
    """
    if use_llm:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "use_llm=True requires ANTHROPIC_API_KEY environment variable. "
                "Either set the key or use rule-based mode (use_llm=False)."
            )
        # LLM-ветка — синхронная обёртка над _extract_with_llm. На практике
        # вызывается редко, для каталогов со сложной разметкой.
        return _extract_with_llm_sync(chunks, brand_hint)

    return _extract_rule_based(chunks, brand_hint)


def _extract_rule_based(
    chunks: list[DocumentChunk],
    brand_hint: str,
) -> list[RawPumpDraft]:
    """Rule-based извлечение из таблиц pdfplumber/docling.

    Идёт за тремя типами таблиц:
        - anchor-таблицы (модель + P_kW)
        - DN/Passage таблица
    Сшивает по нормализованному имени модели.
    """
    # 1) Соберём anchor-строки и DN-карту по всем таблицам всех chunks.
    anchor_rows: list[tuple[str, float | None, int]] = []  # (name, kW, page_no)
    dn_passage_map: dict[str, tuple[float | None, float | None]] = {}

    for chunk in chunks:
        for table in chunk.tables or []:
            page_no = table.get("page_no") or chunk.page_start
            if _is_model_anchor_table(table):
                for name, kw, _row in _extract_anchor_rows(table):
                    anchor_rows.append((name, kw, page_no))
            if _is_dn_passage_table(table):
                dn_passage_map.update(_extract_dn_passage_table(table))

    # 2) Дедупликация по имени модели — один и тот же типоразмер может встречаться
    #    в нескольких таблицах (например, в спецификациях обеих серий /35 и /50,
    #    или в анкер-таблицах под двумя графиками). Берём первую запись со
    #    ВНЯТНОЙ мощностью P_kW (gt 0); если мощности нет — пропускаем.
    deduped: dict[str, tuple[float, list[int]]] = {}
    for name, kw, page_no in anchor_rows:
        if kw is None or kw <= 0:
            continue
        if name in deduped:
            # Накапливаем страницы-источники, мощность не перезаписываем
            existing_kw, pages = deduped[name]
            if page_no not in pages:
                pages.append(page_no)
            deduped[name] = (existing_kw, pages)
        else:
            deduped[name] = (kw, [page_no])

    # 3) Собираем драфты в детерминированном порядке (отсортируем по имени).
    drafts: list[RawPumpDraft] = []
    for name in sorted(deduped.keys()):
        kw, pages = deduped[name]
        # Lookup DN/passage по three-phase ключу
        lookup_key = name if not name.startswith("VXm") else "VX " + name.split(" ", 1)[1]
        dn, passage = dn_passage_map.get(lookup_key, (None, None))

        is_single_phase = name.startswith("VXm")
        voltage = 230 if is_single_phase else 380
        phase = 1 if is_single_phase else 3

        # free_passage_mm обязателен — если по какой-то причине не нашли,
        # ставим дефолт по серии (40 для /35, 50 для /50). Это последний
        # форс-мажорный фолбэк, чтобы не крашнуть Pydantic-валидацию.
        if passage is None:
            series = name.split("/")[-1]
            passage = 40.0 if series == "35" else 50.0

        draft = RawPumpDraft(
            brand=brand_hint,
            model=name,
            free_passage_mm=passage,
            P_kW=kw,
            voltage_v=voltage,
            phase=phase,
            discharge_DN_mm=dn,
        )
        # _source_pages — приватный атрибут, заполняем после конструирования
        draft._source_pages = sorted(pages)
        drafts.append(draft)

    return drafts


# ----------- LLM-режим (опциональный) --------------------------------------


def _extract_with_llm_sync(
    chunks: list[DocumentChunk],
    brand_hint: str,
) -> list[RawPumpDraft]:
    """Синхронная обёртка над Pydantic-AI агентом.

    Вызывается только если `use_llm=True` и ANTHROPIC_API_KEY присутствует.
    Импорт `pydantic_ai` отложен внутрь функции, чтобы rule-based ветка не
    зависела от установки `pydantic-ai` (и тестировалась без сети).
    """
    import asyncio

    return asyncio.run(_extract_with_llm_async(chunks, brand_hint))


async def _extract_with_llm_async(
    chunks: list[DocumentChunk],
    brand_hint: str,
) -> list[RawPumpDraft]:
    """Асинхронная реализация LLM-ветки на Pydantic-AI.

    Не покрывается тестами против реальной сети: для проверки use_llm-кода
    тесты используют `pydantic_ai.models.test.TestModel` либо проверяют только
    error-path при отсутствии ключа.
    """
    from pydantic_ai import Agent

    agent: Agent[None, list[RawPumpDraft]] = Agent(
        "anthropic:claude-haiku-4-5-20251001",
        system_prompt=(
            "Ты извлекаешь записи насосов из markdown PDF-каталога. "
            f"Бренд для всех записей: '{brand_hint}'. "
            "Возвращай list[RawPumpDraft] строго по схеме. Все поля кроме "
            "qh_curve обязательны. Если данных недостаточно — пропусти модель, "
            "не выдумывай."
        ),
        result_type=list[RawPumpDraft],
    )

    drafts: list[RawPumpDraft] = []
    for chunk in chunks:
        # Ограничиваем размер промпта — markdown больших каталогов может
        # съесть весь контекст модели. 8000 символов хватает на 1 страницу
        # с таблицей моделей.
        text = (chunk.markdown or "")[:8000]
        if not text.strip():
            continue
        result = await agent.run(text)
        drafts.extend(result.output)
    return drafts
