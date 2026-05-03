"""Antarus НК (HK) extractor — российский каталог канализационных насосов.

Особенность Antarus: Q, H, free_passage, P_kW и поломочное напряжение
**закодированы прямо в имени модели**:
    HK1-50-10-10-0,75-10M
    │   │  │  │  │    └── глубина погружения 10 м (10M)
    │   │  │  │  └────── мощность двигателя 0.75 кВт
    │   │  │  └───────── max free passage 10 мм
    │   │  └──────────── номинальный напор H = 10 м
    │   └─────────────── номинальная подача Q = 50 м³/ч
    └─────────────────── серия (НК1, НК2)

Опциональный суффикс перед глубиной:
    -TB-  : tropical/sealed motor (в климатическом исполнении)
    -E-   : explosion-proof (ATEX)

PDF (с-о-к.ru мирор) использует mapping fonts, где русское «НК» отображается
как латинское «HK» — нормализуем оба варианта через regex character class.

Q-H у Antarus в каталоге даны как **только envelope** (Q_nom, H_nom в
названии модели) — без полной кривой. Поэтому extractor генерирует stub
Q-H аналогично KSB: parabolic envelope из (Q_nom, H_nom), помеченный
needs_review.
"""

from __future__ import annotations

import re

from pump_calculator.etl.pdf.docling_runner import DocumentChunk
from pump_calculator.etl.pdf.table_extractor import RawPumpDraft
from pump_calculator.etl.schemas import QHPoint

# ---------------------------------------------------------------------------
# Regex для разбора имени модели Antarus
# ---------------------------------------------------------------------------

# Имя модели Antarus НК/HK:
#   HK1-50-10-10-0,75-10M    (без модификации)
#   HK1-100-15-65-5,5-TB-10M (TB вариант)
#   НК2-300-23-1000-90-TB-10М (3-цифры для крупных, кириллица М на конце)
#
# Шаблон: [HK|НК](?:1|2)-Q-H-passage-P_kW(-[TB|E])?-(depth)[MМ]
ANTARUS_MODEL_RE = re.compile(
    r"\b(?P<series>(?:HK|НК)(?:[12]))-"
    r"(?P<q>\d{1,4})-"
    r"(?P<h>\d{1,3})-"
    r"(?P<passage>\d{1,4})-"
    r"(?P<p_kw>\d+(?:[,.]\d+)?)"
    r"(?:-(?P<variant>TB|E))?"
    r"-(?P<depth>\d{1,3})[MМ]\b"
)


def _parse_float_ru(s: str) -> float:
    """'5,5' → 5.5; '0,75' → 0.75."""
    return float(s.replace(",", "."))


def _normalize_series(raw: str) -> str:
    """'HK1' → 'НК1' (унификация на кириллицу — каноническая форма)."""
    return raw.replace("HK", "НК")


def _build_model_name(
    series: str,
    q: str,
    h: str,
    passage: str,
    p_kw: str,
    variant: str | None,
    depth: str,
) -> str:
    """Каноническое имя модели для нашей БД.

    Например: НК1 50/10 (3.0 кВт, 10м, TB)
    """
    series_canon = _normalize_series(series)
    base = f"{series_canon} {q}/{h}"
    suffix_parts = [f"{p_kw} кВт", f"{depth}м"]
    if variant:
        suffix_parts.append(variant)
    suffix = ", ".join(suffix_parts)
    return f"{base} ({suffix})"


def _classify_impeller(series: str, q: float, passage: float) -> str:
    """Классификация типа импеллера по серии и параметрам.

    НК1 — одноканальное закрытое (sewage с волокном)
    НК2 — многоканальное (предочищенные стоки, ливнёвка) или vortex для
          малого free_passage
    """
    if series.endswith("1"):
        return "single-channel"
    if passage < 30:
        return "vortex"
    return "multi-channel"


def _wastewater_compat(series: str, passage: float) -> list[str]:
    """Совместимость с типами стоков по типу серии и проходу."""
    if passage >= 50:
        return ["domestic", "industrial", "drainage"]
    if passage >= 20:
        return ["domestic", "industrial"]
    return ["industrial", "drainage"]  # малый passage → предочищенные


def _build_stub_qh_curve(q_nom: float, h_nom: float) -> list[QHPoint]:
    """Stub Q-H envelope из номинальной точки.

    Antarus каталог не публикует полную Q-H — только nominal Q и H в имени.
    Генерируем 5 точек parabolic envelope с допущением:
        - Shutoff head = 1.25 × H_nom (типично для одноканальных)
        - Q_runout = 1.5 × Q_nom
        - H(Q) = H_shutoff × (1 - 0.7 × (Q/Q_runout)²)

    Помечается NEEDS REVIEW в notes.
    """
    h_shutoff = h_nom * 1.25
    q_runout = q_nom * 1.5

    def h_at(q: float) -> float:
        if q <= 0:
            return h_shutoff
        return round(h_shutoff * (1 - 0.7 * (q / q_runout) ** 2), 2)

    q_points = [0.0, q_nom * 0.5, q_nom, q_nom * 1.25, q_runout]
    return [QHPoint(Q_m3h=round(q, 1), H_m=h_at(q)) for q in q_points]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_antarus_pumps_from_chunks(
    chunks: list[DocumentChunk],
    brand_hint: str = "Antarus",
) -> list[RawPumpDraft]:
    """Извлечь модели Antarus НК из таблиц/текста PDF.

    Алгоритм:
        1. Собираем весь текст всех chunks
        2. Применяем ANTARUS_MODEL_RE к каждой строке
        3. Дедуплицируем по канонической форме (series, q, h)
        4. Парсим параметры из match.groups
        5. Строим RawPumpDraft

    Returns:
        list[RawPumpDraft] — каждая запись имеет stub Q-H envelope
        (помечена NEEDS REVIEW для замены реальной кривой из паспорта).
    """
    seen: set[tuple[str, str, str]] = set()  # (series, q, h)
    drafts: list[RawPumpDraft] = []

    for chunk in chunks:
        md = chunk.markdown or ""
        for match in ANTARUS_MODEL_RE.finditer(md):
            series_raw = match.group("series")
            q_str = match.group("q")
            h_str = match.group("h")
            passage_str = match.group("passage")
            p_kw_str = match.group("p_kw")
            variant = match.group("variant")
            depth_str = match.group("depth")

            series_canon = _normalize_series(series_raw)
            key = (series_canon, q_str, h_str)
            if key in seen:
                continue
            seen.add(key)

            try:
                q_nom = float(q_str)
                h_nom = float(h_str)
                passage = float(passage_str)
                p_kw = _parse_float_ru(p_kw_str)
            except ValueError:
                continue

            if p_kw <= 0:
                continue
            if passage < 1 or passage > 200:
                continue

            model_name = _build_model_name(
                series_raw, q_str, h_str, passage_str, p_kw_str, variant, depth_str
            )
            impeller = _classify_impeller(series_canon, q_nom, passage)
            wastewater = _wastewater_compat(series_canon, passage)

            draft = RawPumpDraft(
                brand=brand_hint,
                model=model_name,
                type="submersible_sewage",
                impeller=impeller,
                free_passage_mm=passage,
                P_kW=p_kw,
                voltage_v=380,  # Antarus three-phase
                phase=3,
                ip_rating="IP68",
                discharge_DN_mm=None,  # не закодировано в имени; уточнить из таблиц
                wastewater_compat=wastewater,
                price_segment="mid",  # Antarus — российский средний сегмент
                available_ru_status="official",
                distributor="ANTARUS (antarus.su) / Теплосервис / Vito Group",
                warranty_months=18,
                notes=(
                    f"Antarus {series_canon} Q_nom={q_nom} H_nom={h_nom} "
                    f"passage={passage}mm. NEEDS REVIEW: Q-H stub-кривая "
                    f"(parabolic envelope), заменить реальной кривой из "
                    f"паспорта. DN не извлечён из имени — уточнить."
                ),
            )
            draft._source_pages = [chunk.page_start]
            drafts.append(draft)

    return drafts


def extract_antarus_qh_curves_from_chunks(
    chunks: list[DocumentChunk],
) -> dict[str, list[QHPoint]]:
    """Stub Q-H для всех найденных Antarus моделей."""
    drafts = extract_antarus_pumps_from_chunks(chunks, brand_hint="Antarus")
    curves: dict[str, list[QHPoint]] = {}
    for draft in drafts:
        # Извлечём Q_nom и H_nom из имени модели "НК1 50/10 (3.0 кВт, 10м)"
        m = re.search(r"(\d+)/(\d+)", draft.model)
        if not m:
            continue
        q_nom = float(m.group(1))
        h_nom = float(m.group(2))
        curves[draft.model] = _build_stub_qh_curve(q_nom, h_nom)
    return curves
