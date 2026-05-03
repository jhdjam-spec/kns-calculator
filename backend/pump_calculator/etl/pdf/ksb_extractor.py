"""KSB Amarex KRT extractor — Designation tables → RawPumpDraft.

KSB Type Series Booklet 50Hz (40 страниц) содержит на страницах 18-21
табличные designation tables: каждая строка — один типоразмер с типом
рабочего колеса (S/F/E/D/K/C), материалом, free_passage, рабочими давлениями.

Q-H у KSB представлены ТОЛЬКО графиками (стр 24-32), численных таблиц нет.
Поэтому этот extractor:
    1. Извлекает draft без qh_curve (Q-H заполняется отдельно)
    2. Помечает draft `_engineer_flag=needs_review` через RawPumpDraft.notes
    3. Заполняет envelope через ориентировочные диапазоны из selection chart
       (Q_min, Q_max, H_min, H_max — для каждой подсерии)

Для production-использования каждой импортированной модели нужно:
    a) добавить qh_curve вручную из соответствующей кривой паспорта, либо
    b) дождаться Phase 6.6.2 (curve_digitizer) для автоматизации.

Контракт совпадает с table_extractor — возвращает list[RawPumpDraft],
дальше pipeline сам решит что делать с пустыми qh_curve (отправит
в quarantine, что логично — без Q-H модель в matching не используется).
"""

from __future__ import annotations

import re

from pump_calculator.etl.pdf.docling_runner import DocumentChunk
from pump_calculator.etl.pdf.table_extractor import RawPumpDraft
from pump_calculator.etl.schemas import QHPoint

# ---------------------------------------------------------------------------
# Regex и константы
# ---------------------------------------------------------------------------

# Строка модели KSB в designation table:
#   "40-252 S G 4 7 235 175 - - 10 13 0,03"
#   "100-315 D G, G1 1 75 222 196 10 15 6,8 8,8 0,065"
#
# Pattern:
#   (?P<size>\d{2,3}-\d{3})  size = DN-D2
#   \s+(?P<impeller>[SFEDKC])  impeller code
#   \s+(?P<material>[A-Z][A-Z0-9, ]*)  material variant (G, G1, G2, GH...)
#   \s+(?P<channels>[-\d]+)  number of channels (or '-' for vortex)
#   \s+(?P<free_passage>\d+)  free passage in mm
KRT_ROW_RE = re.compile(
    r"^\s*(?P<size>\d{2,3}-\d{3})\s+"
    r"(?P<impeller>[SFEDKC])\s+"
    r"(?P<material>(?:G|G1|G2|GH|S|B|L)(?:\s*,\s*(?:G|G1|G2|GH|S|B|L))*)\s+"
    r"(?P<channels>[-\d]+)\s+"
    r"(?P<free_passage>\d+)\s+",
    re.MULTILINE,
)

# Маппинг impeller code → human-readable type (для нашей БД)
IMPELLER_MAP = {
    "S": "single-channel",      # S-tube, single-channel
    "F": "vortex",              # Free-Flow vortex
    "E": "single-channel",      # Single-Vane closed
    "D": "single-channel",      # Diagonal (открытое одноканальное)
    "K": "multi-channel",       # Multi-channel closed
    "C": "cutter",              # Cutter
}

# Применимость по типам стоков для каждого импеллера KSB
# (на основе KSB Magazine "Selecting wastewater pump impellers")
WASTEWATER_COMPAT_MAP = {
    "S": ["domestic", "industrial"],                    # сырая канализация с волокном
    "F": ["domestic", "industrial", "drainage"],        # vortex — самый универсальный
    "E": ["domestic", "industrial"],                    # сырые стоки + ил
    "D": ["domestic", "industrial"],                    # сырая + рециркуляция
    "K": ["industrial", "drainage"],                    # предочищенные, ливнёвка
    "C": ["domestic"],                                  # фекальные малых DN
}

# Ориентировочные envelope диапазоны для KSB Amarex KRT по DN
# (из KSB selection chart 50Hz). Используется для stub Q-H curve,
# пока Phase 6.6.2 (curve_digitizer) не извлечёт реальные кривые из графиков.
#
# Формат: dn_threshold → (Q_BEP_m3h, H_max_m, runout_factor_Q)
# H_max — shutoff head; Q_BEP при максимальном КПД; runout_factor_Q — отношение Q_runout к Q_BEP.
KRT_ENVELOPE_BY_DN = [
    # DN <= порог: (Q_BEP, H_shutoff, runout_factor)
    (50, 25.0, 22.0, 1.6),    # KRT 40-50: малые ~3-7.5 кВт
    (80, 70.0, 28.0, 1.6),    # KRT 65-80: средние ~7.5-15 кВт
    (100, 130.0, 32.0, 1.6),  # KRT 100: 11-22 кВт
    (150, 280.0, 38.0, 1.5),  # KRT 150: 22-37 кВт
    (200, 600.0, 45.0, 1.5),  # KRT 200: 37-75 кВт
    (300, 1500.0, 60.0, 1.4), # KRT 250-300: 75-200 кВт
]


def _stub_qh_envelope(dn_mm: float, impeller: str) -> tuple[float, float, float]:
    """Получить (Q_BEP, H_shutoff, runout_factor) для DN.

    Vortex (F) и Cutter (C) дают на ~15% меньше H за тот же Q
    (низкий КПД компенсируется большим free passage).
    """
    for threshold, q_bep, h_shutoff, runout in KRT_ENVELOPE_BY_DN:
        if dn_mm <= threshold:
            if impeller in ("F", "C"):
                h_shutoff *= 0.85
            return q_bep, h_shutoff, runout
    # Fallback — самые большие
    return 1500.0, 60.0, 1.4


def _build_stub_qh_curve(dn_mm: float, impeller: str) -> list[QHPoint]:
    """Сгенерировать 5 stub Q-H точек для KSB модели.

    Параболическая аппроксимация:
        H(Q) = H_shutoff * (1 - 0.7 * (Q/Q_runout)^2)

    Точки: shutoff (Q=0), 25% Q_BEP, BEP, 75% от Q_runout, Q_runout.

    ⚠️ Эти точки СТАБ — реальные данные нужны из Q-H графиков паспорта
    KSB (Phase 6.6.2 curve_digitizer). Все KSB-записи будут иметь
    `_engineer_flag=needs_review` для замены кривых перед production.
    """
    q_bep, h_shutoff, runout_factor = _stub_qh_envelope(dn_mm, impeller)
    q_runout = q_bep * runout_factor

    def h_at(q: float) -> float:
        if q <= 0:
            return h_shutoff
        return round(h_shutoff * (1 - 0.7 * (q / q_runout) ** 2), 2)

    q_points = [0.0, q_bep * 0.5, q_bep, q_bep * 1.3, q_runout]
    return [QHPoint(Q_m3h=round(q, 1), H_m=h_at(q)) for q in q_points]


# ---------------------------------------------------------------------------
# Извлечение моделей из KSB designation tables
# ---------------------------------------------------------------------------


def _is_ksb_designation_page(text: str) -> bool:
    """Эвристика: страница содержит KSB designation table.

    Признаки:
        - Упоминание "Amarex KRT" или "KRT"
        - Заголовок "Size" + "Impeller"
        - >=3 строки с pattern KRT_ROW_RE
    """
    if "KRT" not in text:
        return False
    if "Size" not in text:
        return False
    matches = KRT_ROW_RE.findall(text)
    return len(matches) >= 3


def _parse_dn_from_size(size: str) -> float | None:
    """'40-252' → 40.0 (DN нагнетания, мм)."""
    parts = size.split("-")
    if not parts:
        return None
    try:
        return float(parts[0])
    except ValueError:
        return None


def _build_model_name(size: str, impeller: str) -> str:
    """KSB канонический формат имени для нашей БД.

    Пример: ('40-252', 'F') → 'KRT F 40-252'
    """
    return f"KRT {impeller} {size}"


def _estimate_power_kw(dn_mm: float, impeller: str) -> float:
    """Грубая оценка мощности по DN + типу импеллера.

    KSB Amarex KRT не публикует P_kW в designation table — только в
    отдельной motor table, привязанной по коду мотора. Для draft
    используем приблизительную таблицу:
        DN 40-65 → 1.5-7.5 кВт (берём середину)
        DN 80-100 → 4-15 кВт
        DN 150-200 → 11-37 кВт
        DN 250-300 → 30-90 кВт

    Cutter (C) и vortex (F) на ~10% мощнее за равный Q из-за низкого КПД.
    Это используется ТОЛЬКО для draft; точное значение должен заполнить
    инженер при review.
    """
    if dn_mm <= 50:
        base = 3.0
    elif dn_mm <= 80:
        base = 7.5
    elif dn_mm <= 100:
        base = 11.0
    elif dn_mm <= 150:
        base = 22.0
    elif dn_mm <= 200:
        base = 37.0
    else:
        base = 55.0

    if impeller in ("F", "C"):
        base *= 1.10
    return round(base, 1)


def extract_ksb_qh_curves_from_chunks(
    chunks: list[DocumentChunk],
) -> dict[str, list[QHPoint]]:
    """Сгенерировать stub Q-H кривые для всех KSB моделей в chunks.

    Аналог `qh_extractor.extract_qh_curves_from_chunks`, но для KSB,
    где численных Q-H таблиц нет (только графики). Использует
    `_build_stub_qh_curve` на основе DN и impeller-кода.

    Все сгенерированные кривые — STUB (parabolic envelope), требуют
    замены реальными данными в Phase 6.6.2 (curve_digitizer) или
    через ручной import.

    Returns:
        dict {model_name: [QHPoint, ...]} с теми же model_name, что у
        `extract_ksb_pumps_from_chunks`.
    """
    drafts = extract_ksb_pumps_from_chunks(chunks, brand_hint="KSB")
    curves: dict[str, list[QHPoint]] = {}
    for draft in drafts:
        if not draft.discharge_DN_mm:
            continue
        # Извлечь impeller-код из model_name "KRT F 40-252"
        parts = draft.model.split()
        if len(parts) < 3:
            continue
        impeller_code = parts[1]
        curves[draft.model] = _build_stub_qh_curve(
            dn_mm=draft.discharge_DN_mm,
            impeller=impeller_code,
        )
    return curves


def extract_ksb_pumps_from_chunks(
    chunks: list[DocumentChunk],
    brand_hint: str = "KSB",
) -> list[RawPumpDraft]:
    """Извлечь модели KSB Amarex KRT из designation tables.

    Алгоритм:
        1. Для каждого chunk — собираем markdown
        2. Если страница содержит KRT designation table — парсим строки
        3. Дедуплицируем по (size, impeller) — одна модель = один draft
        4. Заполняем поля: brand, model, type, impeller, free_passage_mm,
           wastewater_compat, P_kW (estimate), DN, price_segment="premium"

    Returns:
        list[RawPumpDraft] (без qh_curve — Q-H у KSB только графики)
    """
    seen: set[tuple[str, str]] = set()
    drafts: list[RawPumpDraft] = []

    for chunk in chunks:
        md = chunk.markdown or ""
        if not _is_ksb_designation_page(md):
            continue

        for match in KRT_ROW_RE.finditer(md):
            size = match.group("size")
            impeller = match.group("impeller")
            free_passage = match.group("free_passage")

            key = (size, impeller)
            if key in seen:
                continue
            seen.add(key)

            try:
                free_passage_mm = float(free_passage)
            except ValueError:
                free_passage_mm = 50.0  # safe fallback

            dn_mm = _parse_dn_from_size(size)
            if dn_mm is None:
                continue

            model_name = _build_model_name(size, impeller)
            impeller_type = IMPELLER_MAP[impeller]
            wastewater_compat = WASTEWATER_COMPAT_MAP[impeller]
            p_kw = _estimate_power_kw(dn_mm, impeller)

            # Whitelist стандартных DN KSB Amarex KRT
            # (по Type Series Booklet 50Hz: 40, 50, 65, 80, 100, 150, 200, 250, 300)
            if dn_mm not in (40, 50, 65, 80, 100, 150, 200, 250, 300):
                continue

            draft = RawPumpDraft(
                brand=brand_hint,
                model=model_name,
                type="submersible_sewage" if impeller != "C" else "submersible_cutter",
                impeller=impeller_type,
                free_passage_mm=free_passage_mm,
                P_kW=p_kw,
                voltage_v=380,  # KSB KRT — three-phase indust
                phase=3,
                ip_rating="IP68",
                discharge_DN_mm=dn_mm,
                wastewater_compat=wastewater_compat,
                price_segment="premium",
                available_ru_status="parallel_import",  # KSB после 2022 — параллельный импорт
                distributor="ksb.nt-rt.ru / Petroplan",
                warranty_months=24,
                notes=(
                    f"KSB Amarex KRT {impeller} (impeller {impeller_type}). "
                    f"NEEDS REVIEW: P_kW=~{p_kw} оценочно по DN; уточнить по motor table. "
                    f"Q-H stub-кривая (parabolic envelope) — заменить реальными данными "
                    f"из Q-H графика паспорта или через Phase 6.6.2 curve_digitizer."
                ),
            )
            draft._source_pages = [chunk.page_start]
            drafts.append(draft)

    return drafts
