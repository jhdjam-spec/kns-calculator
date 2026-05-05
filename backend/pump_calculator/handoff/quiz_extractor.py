"""Парсер заполненного DOCX-опросника обратно в L0Input + L1Input + metadata.

Пара к `questionnaire_docx.py`. Полагается на стабильные machine-readable коды
в первой колонке таблиц (например `Q_M3H`, `WASTEWATER_TYPE`).

Возвращает:
- L0Input, L1Input — для немедленного вызова /select
- metadata: object_name, client_company, city и т.д. — для сохранения в КП/PDF BOM
- missing_fields: коды полей, которых не нашли (для UI «уточните вручную»)
- raw_codes: полный dict {code → str} для отладки
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Any

from docx import Document

from pump_calculator.schemas import L0Input, L1Input, WastewaterType

# Карта алиасов для типа стоков — клиент может вписать русское или английское
WASTEWATER_ALIASES: dict[str, WastewaterType] = {
    # английские
    "domestic": "domestic",
    "drainage": "drainage",
    "industrial": "industrial",
    "clean_water": "clean_water",
    # русские варианты
    "хоз-бытовые": "domestic",
    "хоз бытовые": "domestic",
    "хоз. бытовой": "domestic",
    "хозбытовые": "domestic",
    "бытовые": "domestic",
    "бытовая": "domestic",
    "ливневая": "drainage",
    "ливнёвка": "drainage",
    "ливневка": "drainage",
    "ливнёвые": "drainage",
    "ливневые": "drainage",
    "ливневый": "drainage",
    "дренажные": "drainage",
    "дренаж": "drainage",
    "производственные": "industrial",
    "производственный": "industrial",
    "промышленные": "industrial",
    "чистая вода": "clean_water",
    "спд": "clean_water",
    "питьевая": "clean_water",
}

# Карта типов труб
PIPE_MATERIAL_ALIASES = {
    "pe100": "pe100_sdr17",
    "pe100_sdr17": "pe100_sdr17",
    "пэ100": "pe100_sdr17",
    "пэ100 sdr17": "pe100_sdr17",
    "сталь": "steel_welded_new",
    "steel": "steel_welded_new",
    "steel_welded_new": "steel_welded_new",
    "steel_seamless_new": "steel_seamless_new",
    "pvc": "pvc",
    "пвх": "pvc",
    "pp": "pp",
    "пп": "pp",
    "корсис": "korsis_pe_corrugated",
    "korsis": "korsis_pe_corrugated",
    "чугун": "cast_iron_new",
    "бетон": "concrete",
    "concrete": "concrete",
}


@dataclass
class ExtractedQuiz:
    """Результат парсинга опросника."""

    L0: L0Input | None = None
    L1: L1Input | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    raw_codes: dict[str, str] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _read_codes_from_docx(file_bytes: bytes) -> dict[str, str]:
    """Прочитать DOCX и вернуть dict {code → value} из всех таблиц.

    Опросник построен так: таблицы 3 колонки (код | метка | значение).
    Парсер берёт всё, что выглядит как код (uppercase + underscore + digit) в колонке 0.
    """
    codes: dict[str, str] = {}
    doc = Document(io.BytesIO(file_bytes))
    code_pattern = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")

    for table in doc.tables:
        for row in table.rows:
            cells = row.cells
            if len(cells) < 3:
                continue
            code_text = cells[0].text.strip()
            value_text = cells[2].text.strip()
            if code_pattern.match(code_text):
                # При повторе кода (теоретически невозможно в нашем шаблоне) — берём первое значение
                if code_text not in codes:
                    codes[code_text] = value_text
    return codes


def _parse_float(s: str) -> float | None:
    """'21,2 м³/ч' → 21.2; 'нет' → None; пусто → None."""
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    # Заменим запятую на точку, удалим всё кроме цифр, точки, минуса
    cleaned = re.sub(r"[^\d.,\-]", "", s.replace(",", "."))
    if not cleaned:
        return None
    # На случай нескольких точек/минусов оставляем первую группу
    m = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _parse_yes_no(s: str) -> bool | None:
    if not s:
        return None
    s = s.strip().lower()
    if s in {"да", "yes", "true", "+", "1", "y"}:
        return True
    if s in {"нет", "no", "false", "-", "0", "n"}:
        return False
    return None


def _parse_wastewater(s: str) -> WastewaterType | None:
    if not s:
        return None
    s_low = s.strip().lower()
    if s_low in WASTEWATER_ALIASES:
        return WASTEWATER_ALIASES[s_low]
    # частичное совпадение по подстроке
    for alias, canonical in WASTEWATER_ALIASES.items():
        if alias in s_low:
            return canonical
    return None


def _parse_pipe_material(s: str) -> str | None:
    if not s:
        return None
    s_low = s.strip().lower()
    if s_low in PIPE_MATERIAL_ALIASES:
        return PIPE_MATERIAL_ALIASES[s_low]
    for alias, canonical in PIPE_MATERIAL_ALIASES.items():
        if alias in s_low:
            return canonical
    return None


def _parse_corpus_material(s: str) -> str | None:
    if not s:
        return None
    s_low = s.strip().lower()
    if "glass" in s_low or "стеклопласт" in s_low:
        return "glass"
    if s_low in {"pe", "пэ"} or "пэ" in s_low or "полиэтилен" in s_low:
        return "pe"
    return None


def _parse_redundancy(s: str) -> str | None:
    if not s:
        return None
    s_clean = re.sub(r"[^\d+N]", "", s.strip().upper())
    if s_clean in {"1+0", "1+1", "2+1", "3+1", "N+0"}:
        return s_clean
    return None


def _parse_reliability_category(s: str) -> str | None:
    if not s:
        return None
    s_clean = s.strip().upper()
    # Берём первую римскую цифру
    m = re.search(r"\bI{1,3}\b", s_clean)
    if m and m.group(0) in {"I", "II", "III"}:
        return m.group(0)
    return None


def parse_questionnaire_docx(file_bytes: bytes) -> ExtractedQuiz:
    """Распарсить заполненный клиентом DOCX-опросник.

    Возвращает ExtractedQuiz, в котором:
    - L0: пригодный к /select запрос (None если Q не извлечён — обязательное поле)
    - L1: опциональные поля
    - metadata: object_name, client_company и т.д.
    - missing_fields: какие поля не нашли (для UI)
    """
    out = ExtractedQuiz()
    out.raw_codes = _read_codes_from_docx(file_bytes)

    # ---- L0: расход ----
    Q_m3h = _parse_float(out.raw_codes.get("Q_M3H", ""))
    Q_ls = _parse_float(out.raw_codes.get("Q_LS", ""))
    Q_m3sut = _parse_float(out.raw_codes.get("Q_M3SUT", ""))

    if Q_m3h is None and Q_ls is not None:
        Q_m3h = Q_ls * 3.6
        out.warnings.append(
            f"Q извлечён из Q_LS ({Q_ls} л/с) → {Q_m3h:.2f} м³/ч"
        )
    if Q_m3h is None and Q_m3sut is not None:
        Q_m3h = Q_m3sut / 24.0
        out.warnings.append(
            f"Q извлечён из Q_M3SUT ({Q_m3sut} м³/сут) → {Q_m3h:.2f} м³/ч (среднесуточный, не пиковый)"
        )

    # ---- L0: напор и геометрия ----
    dH_m = _parse_float(out.raw_codes.get("DH_M", ""))
    L_m = _parse_float(out.raw_codes.get("L_M", ""))
    H_m = _parse_float(out.raw_codes.get("H_M", ""))

    # Если задан полный H и НЕТ ΔH+L — конвертируем в ΔH (упрощение, но клиент так часто пишет)
    if dH_m is None and L_m is None and H_m is not None:
        dH_m = H_m
        L_m = 0.0
        out.warnings.append(
            f"Заполнено только H={H_m} м, ΔH+L пустые — используем dH={H_m}, L=0 "
            "(подбор по полному напору без расчёта потерь по трассе)"
        )

    # ---- L0: тип стоков ----
    wastewater = _parse_wastewater(out.raw_codes.get("WASTEWATER_TYPE", ""))

    # Проверка минимального набора для L0
    missing = []
    if Q_m3h is None:
        missing.append("Q_M3H")
    if not missing:
        out.L0 = L0Input(
            Q_m3h=Q_m3h,
            dH_m=dH_m,
            L_m=L_m,
            wastewater_type=wastewater,
        )

    # ---- L1: опциональные ----
    L1_kwargs: dict[str, Any] = {}

    pipe_material = _parse_pipe_material(out.raw_codes.get("PIPE_MATERIAL", ""))
    if pipe_material:
        L1_kwargs["pipe_material"] = pipe_material

    pipe_D_mm = _parse_float(out.raw_codes.get("PIPE_D_MM", ""))
    if pipe_D_mm is not None:
        L1_kwargs["pipe_D_mm"] = pipe_D_mm

    corpus_material = _parse_corpus_material(out.raw_codes.get("CORPUS_MATERIAL", ""))
    if corpus_material:
        L1_kwargs["corpus_material"] = corpus_material

    redundancy = _parse_redundancy(out.raw_codes.get("REDUNDANCY", ""))
    if redundancy:
        L1_kwargs["redundancy"] = redundancy

    reliability = _parse_reliability_category(out.raw_codes.get("RELIABILITY_CATEGORY", ""))
    if reliability:
        L1_kwargs["reliability_category"] = reliability

    ex_required = _parse_yes_no(out.raw_codes.get("EX_REQUIRED", ""))
    if ex_required is True:
        L1_kwargs["Ex_required"] = True

    liquid_temp = _parse_float(out.raw_codes.get("LIQUID_TEMP_C", ""))
    if liquid_temp is not None:
        L1_kwargs["liquid_temp_c"] = liquid_temp

    if L1_kwargs:
        out.L1 = L1Input(**L1_kwargs)

    # ---- metadata ----
    for code in ("OBJECT_NAME", "CLIENT_COMPANY", "CLIENT_CONTACT", "CITY", "KP_NUMBER", "FILL_DATE"):
        v = out.raw_codes.get(code, "").strip()
        if v:
            out.metadata[code] = v

    # ---- missing_fields для UI ----
    out.missing_fields = missing
    if dH_m is None and H_m is None:
        out.missing_fields.append("DH_M_OR_H_M")
    if not wastewater:
        out.missing_fields.append("WASTEWATER_TYPE")

    return out
