"""TZ Parser — извлечение Q/H/город/тип стоков из произвольного ТЗ.

Назначение
==========
Менеджер вставляет ТЗ или опросный лист в /import — backend парсит
Q (м³/ч), H (м), город, тип стоков, шифр проекта, упомянутые производители,
требования ATEX/категория надёжности/температура жидкости.

Результат — `TZParseResult`, который фронт мапит на L0/L1 wizard
через URL-параметры (`/project?preset=auto&q=…&dh=…&city=…`).

Изоляция
========
- Не зависит от matching/pricing/wizard pipeline.
- Переиспользует regex для шифров проектов из `incoming_classifier`.
- Опционально подгружает список 76 городов из `climate_simulator`
  (graceful fallback если dataset недоступен).
"""
from __future__ import annotations

import re
from typing import Final

from pydantic import BaseModel, Field

from pump_calculator.etl.incoming_classifier import (
    MANUFACTURER_MARKERS,
    OBJECT_MARKERS,
    extract_project_codes,
)

# ---------------------------------------------------------------------------
# Регексы: расход Q
# ---------------------------------------------------------------------------
#
# Допустимые форматы:
#   Q=88.6 м³/ч / Q = 88,6 м3/ч / расход 25 л/с / Производительность 18 m3/h
#   88 м³/час / 100 куб/час / 25 л/сек / 240 м³/сут (сутки)
#   Q=88.6 / напор 39 м (Q без единицы — менее надёжно, идёт fallback)
#
# Возвращаемое значение приводится к м³/ч.

_RE_Q_M3H: Final[re.Pattern[str]] = re.compile(
    r"(?:Q|q|расход|производ\w*|пропуск\w*|подача)\s*[=:\s]*\s*"
    r"(\d+(?:[\.,]\d+)?)\s*"
    r"(?:м\s*[³3]\s*/\s*(?:ч|час)|m\s*3\s*/\s*h|куб(?:ометр)?\w*\s*в\s*час)",
    re.IGNORECASE,
)

_RE_Q_LS: Final[re.Pattern[str]] = re.compile(
    r"(?:Q|q|расход|производ\w*)\s*[=:\s]*\s*"
    r"(\d+(?:[\.,]\d+)?)\s*л\s*/\s*с(?:ек)?",
    re.IGNORECASE,
)

_RE_Q_M3SUT: Final[re.Pattern[str]] = re.compile(
    r"(?:Q|q|расход|производ\w*)\s*[=:\s]*\s*"
    r"(\d+(?:[\.,]\d+)?)\s*"
    r"(?:м\s*[³3]\s*/\s*сут(?:ки|ок)?|куб\w*\s*/\s*сут\w*)",
    re.IGNORECASE,
)

# Q без явного маркера, но с единицей: «88,6 м³/ч в час»
_RE_Q_NAKED_M3H: Final[re.Pattern[str]] = re.compile(
    r"(\d+(?:[\.,]\d+)?)\s*м\s*[³3]\s*/\s*(?:ч|час)",
)

_RE_Q_NAKED_LS: Final[re.Pattern[str]] = re.compile(
    r"(\d+(?:[\.,]\d+)?)\s*л\s*/\s*с(?:ек)?(?![А-Яа-яa-zA-Z])",
)

# ---------------------------------------------------------------------------
# Регексы: напор H
# ---------------------------------------------------------------------------
#
# Допустимые форматы:
#   H=39 м / H = 39,5 м / напор 39 м / dH=39 / геом. высота 12 м
#   high lift 39 м / 39 м водяного столба / H = 39
_RE_H: Final[re.Pattern[str]] = re.compile(
    r"(?:dH|d\.H|H|напор\w*|высот\w*\s*подъёма|подъём)\s*[=:\s]*\s*"
    r"(\d+(?:[\.,]\d+)?)\s*"
    r"(?:м(?:етр\w*)?(?:\s*вод\w*\s*столб\w*)?|m\.?)\b",
    re.IGNORECASE,
)

# H без явного маркера: «напор 39»
_RE_H_NAKED: Final[re.Pattern[str]] = re.compile(
    r"напор\w*\s*[=:]?\s*(\d+(?:[\.,]\d+)?)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Тип стоков (wastewater type)
# ---------------------------------------------------------------------------
WASTEWATER_MARKERS: Final[dict[str, tuple[str, ...]]] = {
    # ключи совпадают с L0.wastewater_type enum
    "domestic": ("бытов", "хоз-быт", "хозбыт", "хоз\\.быт", "канализация жилого", "жилого комплекс"),
    "industrial": ("промышл", "индустр", "технолог\\w*\\s*сток", "производственн"),
    "drainage": ("ливнев", "дожд\\w*\\s*сток", "поверхностн\\w*\\s*сток", "дренаж"),
    "fire_protection": ("пожар", "пожарн"),
    "clean_water": ("чист\\w*\\s*вод", "питьев", "хозпитьев"),
}

# ---------------------------------------------------------------------------
# Температура жидкости
# ---------------------------------------------------------------------------
_RE_LIQUID_TEMP: Final[re.Pattern[str]] = re.compile(
    r"температур\w*\s+(?:жидкост\w*|стоков|воды|перекачив\w*\s*сред\w*)"
    r"\s*[=:\-—]?\s*([+-]?\d+(?:[\.,]\d+)?)\s*°?\s*[CС]?",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Категория надёжности (СП 31, ПУЭ)
# Форматы:
#   «I категория надёжности» / «I-я категория»
#   «категория надёжности: I» / «категория надёжности — II»
# ---------------------------------------------------------------------------
_RE_RELIABILITY_PRE: Final[re.Pattern[str]] = re.compile(
    r"\b(I{1,3})\s*(?:-\s*[ая])?\s*катего\w*(?:\s*надёжн\w*|\s*электроснабж\w*)?",
)
_RE_RELIABILITY_POST: Final[re.Pattern[str]] = re.compile(
    r"катего\w*\s*(?:надёжн\w*|электроснабж\w*)?\s*[:\-—]?\s*\b(I{1,3})\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# ATEX / взрывозащита
# ---------------------------------------------------------------------------
_ATEX_MARKERS: Final[tuple[str, ...]] = (
    "взрывозащищ", "взрывобезопас", "atex", "ex-исп", "ехисп",
    "ex d", "ex e", "1ex", "2ex", "iib", "iic", "взрыв\\w*\\s*зон",
)

# ---------------------------------------------------------------------------
# Города — lazy-load 76 городов из climate_cities_2026.json
# ---------------------------------------------------------------------------


def _city_names() -> list[str]:
    """Список городов из climate dataset (lowercase). Graceful fallback."""
    try:
        from pump_calculator.climate_simulator import _city_index  # noqa: PLC0415

        return list(_city_index().keys())
    except Exception:  # noqa: BLE001
        # Fallback minimal список топ-городов на случай поломки dataset
        return [
            "москва", "санкт-петербург", "краснодар", "ростов-на-дону",
            "казань", "екатеринбург", "новосибирск", "сочи", "симферополь",
            "ялта", "евпатория", "севастополь",
        ]


def _normalize_city_token(s: str) -> str:
    return s.strip().lower().replace("ё", "е")


def _detect_city(text: str) -> str | None:
    """Поиск города по списку 76 городов dataset.

    Стратегия:
    1. Regex `г\\.?\\s*(\\w+)` или «город X» → проверить против списка.
    2. Иначе — пройтись по списку (от длинных к коротким) и искать substring.
    """
    if not text:
        return None
    norm_text = text.lower().replace("ё", "е")
    cities = sorted(_city_names(), key=len, reverse=True)

    # Priority 1: «г. Краснодар» / «город Краснодар»
    explicit = re.findall(
        r"(?:^|[\s,;:.])(?:г\.?\s*|город\s+)([А-Яа-я][А-Яа-я\-]{2,30})",
        text,
    )
    for token in explicit:
        cand = _normalize_city_token(token)
        # match по полному совпадению или substring
        for city in cities:
            cnorm = _normalize_city_token(city)
            if cnorm == cand or cnorm.startswith(cand) or cand.startswith(cnorm):
                # Возвращаем оригинальное название из dataset (capitalize)
                return city.capitalize() if city.islower() else city

    # Priority 2: substring search по списку
    for city in cities:
        cnorm = _normalize_city_token(city)
        if len(cnorm) < 4:
            continue
        # word boundary: до и после — не буква
        pattern = rf"(?:^|[^а-яё]){re.escape(cnorm)}(?:[^а-яё]|$)"
        if re.search(pattern, norm_text):
            return city.capitalize() if city.islower() else city
    return None


# ---------------------------------------------------------------------------
# Public schema
# ---------------------------------------------------------------------------


class TZParseResult(BaseModel):
    """Результат парсинга ТЗ — pre-fill для Wizard L0/L1.

    Все числовые поля приведены к внутренним единицам (Q → м³/ч, H → м).
    `confidence` — доля заполненных ключевых полей (Q, H, city, wastewater_type)
    из 4 возможных. `fields_found` — какие именно поля удалось извлечь.
    """

    Q_m3h: float | None = Field(None, description="Расход, м³/ч")
    dH_m: float | None = Field(None, description="Напор, м (геом. + потери)")
    city: str | None = Field(None, description="Город из climate_cities_2026.json")
    wastewater_type: str | None = Field(
        None,
        description="domestic | industrial | drainage | fire_protection | clean_water",
    )
    project_code: str | None = Field(None, description="Первый найденный шифр проекта")
    project_codes: list[str] = Field(default_factory=list, description="Все шифры")
    object_type: str | None = Field(None, description="КНС | ЛОС | ВНС | ...")
    manufacturer: str | None = Field(None, description="Упомянутый производитель")
    Ex_required: bool = Field(False, description="Требуется взрывозащита (ATEX/Ex)")
    reliability: str | None = Field(None, description="I | II | III категория надёжности")
    liquid_temp_c: float | None = Field(None, description="Температура жидкости, °C")
    extracted_text_chars: int = Field(0, description="Длина исходного текста")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="0..1 — доля ключевых полей")
    fields_found: list[str] = Field(default_factory=list, description="['Q', 'H', 'city', ...]")
    raw_matches: dict = Field(default_factory=dict, description="Сырые regex-совпадения для debug")


# ---------------------------------------------------------------------------
# Helpers — нормализация чисел
# ---------------------------------------------------------------------------


def _to_float(s: str) -> float:
    """«88,6» / «88.6» → 88.6."""
    return float(s.replace(",", "."))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_tz(text: str) -> TZParseResult:
    """Извлечь из произвольного ТЗ Q/H/город/тип/шифр/доп.параметры.

    Алгоритм:
    1. Q — пытаемся в порядке: с маркером м³/ч → м³/сут (÷24) → л/с (×3.6)
       → naked м³/ч (если других нет) → naked л/с.
    2. H — с маркером «напор/H» и единицей «м» → naked «напор N».
    3. City — список 76 городов; приоритет «г. X» / «город X».
    4. Wastewater type — keywords (бытов/промыш/ливнев/пожар/чист).
    5. Шифры — extract_project_codes.
    6. Object/manufacturer — переиспользуем словари из incoming_classifier.
    7. Ex_required / reliability / liquid_temp — отдельные regex.

    Returns
    -------
    TZParseResult с confidence ∈ [0, 1] от 4 ключевых полей.
    """
    if not text:
        return TZParseResult(confidence=0.0, extracted_text_chars=0)

    raw: dict = {}
    fields: list[str] = []

    # --- Q (м³/ч) ---
    Q: float | None = None
    if (m := _RE_Q_M3H.search(text)):
        Q = _to_float(m.group(1))
        raw["Q_match"] = m.group(0)
    elif (m := _RE_Q_M3SUT.search(text)):
        Q = round(_to_float(m.group(1)) / 24.0, 2)
        raw["Q_match"] = m.group(0) + " → м³/ч ÷24"
    elif (m := _RE_Q_LS.search(text)):
        Q = round(_to_float(m.group(1)) * 3.6, 2)
        raw["Q_match"] = m.group(0) + " → м³/ч ×3.6"
    elif (m := _RE_Q_NAKED_M3H.search(text)):
        Q = _to_float(m.group(1))
        raw["Q_match"] = m.group(0) + " (naked)"
    elif (m := _RE_Q_NAKED_LS.search(text)):
        Q = round(_to_float(m.group(1)) * 3.6, 2)
        raw["Q_match"] = m.group(0) + " (naked l/s)"
    if Q is not None:
        fields.append("Q")

    # --- H (м) ---
    H: float | None = None
    if (m := _RE_H.search(text)):
        H = _to_float(m.group(1))
        raw["H_match"] = m.group(0)
    elif (m := _RE_H_NAKED.search(text)):
        H = _to_float(m.group(1))
        raw["H_match"] = m.group(0) + " (naked)"
    if H is not None:
        fields.append("H")

    # --- City ---
    city = _detect_city(text)
    if city:
        fields.append("city")
        raw["city_match"] = city

    # --- Wastewater type ---
    wastewater: str | None = None
    lower = text.lower()
    for ws_type, patterns in WASTEWATER_MARKERS.items():
        for pat in patterns:
            if re.search(pat, lower):
                wastewater = ws_type
                break
        if wastewater:
            break
    if wastewater:
        fields.append("wastewater_type")
        raw["wastewater_match"] = wastewater

    # --- Project codes ---
    codes = extract_project_codes(text)
    project_code = codes[0] if codes else None
    if project_code:
        raw["project_code"] = project_code

    # --- Object type (КНС/ЛОС/ВНС) ---
    object_type: str | None = None
    for key, markers in OBJECT_MARKERS.items():
        for marker in markers:
            if marker.lower() in lower:
                object_type = key
                break
        if object_type:
            break
    if object_type:
        raw["object_type"] = object_type

    # --- Manufacturer ---
    manufacturer: str | None = None
    for key, markers in MANUFACTURER_MARKERS.items():
        for marker in markers:
            if marker.lower() in lower:
                manufacturer = key
                break
        if manufacturer:
            break
    if manufacturer:
        raw["manufacturer"] = manufacturer

    # --- Ex / ATEX ---
    Ex_required = False
    for marker in _ATEX_MARKERS:
        if re.search(marker, lower):
            Ex_required = True
            raw["Ex_marker"] = marker
            break

    # --- Reliability category ---
    reliability: str | None = None
    if (m := _RE_RELIABILITY_PRE.search(text)):
        reliability = m.group(1)  # «I», «II», «III»
        raw["reliability_match"] = m.group(0)
    elif (m := _RE_RELIABILITY_POST.search(text)):
        reliability = m.group(1)
        raw["reliability_match"] = m.group(0)

    # --- Liquid temperature ---
    liquid_temp: float | None = None
    if (m := _RE_LIQUID_TEMP.search(text)):
        liquid_temp = _to_float(m.group(1))
        raw["liquid_temp_match"] = m.group(0)

    # --- Confidence: 4 ключевых поля (Q, H, city, wastewater_type) ---
    core_fields = {"Q", "H", "city", "wastewater_type"}
    found_core = sum(1 for f in fields if f in core_fields)
    confidence = round(found_core / 4.0, 2)

    return TZParseResult(
        Q_m3h=Q,
        dH_m=H,
        city=city,
        wastewater_type=wastewater,
        project_code=project_code,
        project_codes=codes,
        object_type=object_type,
        manufacturer=manufacturer,
        Ex_required=Ex_required,
        reliability=reliability,
        liquid_temp_c=liquid_temp,
        extracted_text_chars=len(text),
        confidence=confidence,
        fields_found=fields,
        raw_matches=raw,
    )
