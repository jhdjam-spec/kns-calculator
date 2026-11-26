"""Хелперы форматирования чисел и enum-ключей для UX-сообщений (warnings,
suggestions, etc). Цель: избавиться от «Q=205.20000000000002 м³/ч» и
«сброс в 'municipal_sewage'» — float precision tails и raw enum keys
не должны попадать к пользователю.
"""

from __future__ import annotations

import urllib.parse


def cd_filename(filename: str) -> str:
    """Content-Disposition с поддержкой кириллицы по RFC 5987.

    HTTP-заголовки могут содержать только latin-1; для имени файла с не-ASCII
    нужен и ASCII-fallback, и filename* с UTF-8 percent-encoding. Без этого
    Starlette/uvicorn падают с UnicodeEncodeError ('latin-1' codec can't encode).

    Пример вывода:
        attachment; filename="report.pdf"; filename*=UTF-8''%D0%9E%D1%82%D1%87...
    """
    ascii_fallback = (
        filename.encode("ascii", "replace").decode("ascii").replace("?", "_")
    )
    encoded = urllib.parse.quote(filename, safe="")
    return (
        f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'
    )


def fmt_q(q_m3h: float | int | None) -> str:
    """Формат расхода Q [м³/ч] — 1 знак после запятой, без хвоста.
    Примеры: 205.20000000000002 → "205.2", 21.2 → "21.2", 100 → "100".
    """
    if q_m3h is None:
        return "—"
    rounded = round(float(q_m3h), 1)
    if rounded.is_integer():
        return f"{int(rounded)}"
    return f"{rounded:g}"


def fmt_num(x: float | int | None, decimals: int = 1) -> str:
    """Общий формат числа с N знаков. Убирает float-tails."""
    if x is None:
        return "—"
    rounded = round(float(x), decimals)
    if rounded.is_integer():
        return f"{int(rounded)}"
    return f"{rounded:g}"


# Человеко-читаемые названия для enum-keys target_discharge.
# Источник: schemas.py L1Input.target_discharge.
TARGET_DISCHARGE_LABELS = {
    "municipal_sewage": "городскую канализацию",
    "fishery_water": "рыбохозяйственный водоём",
    "general_use": "водоём общего пользования",
    "industrial_reuse": "повторное использование",
    "irrigation": "полив сельхозземель",
    "soil": "грунт (фильтрационное поле)",
}


def fmt_target_discharge(target: str | None) -> str:
    """Преобразует ключ target_discharge в человекочитаемое название.
    Примеры: "municipal_sewage" → "городскую канализацию"."""
    if not target:
        return "—"
    return TARGET_DISCHARGE_LABELS.get(target, target)


# Человеко-читаемые названия для L1.* машинных ключей (используются как
# заголовки suggestion-карточек на /project/).
L1_FIELD_LABELS = {
    "disinfection": "Обеззараживание сточных вод",
    "phosphorus_removal": "Удаление фосфора",
    "nitrification": "Нитрификация / денитрификация",
    "denitrification": "Денитрификация",
    "target_discharge": "Точка сброса",
    "ex_zone_class": "Класс взрывозащиты",
    "ex_temp_class": "Температурный класс",
    "soil_type": "Тип грунта",
    "groundwater_level_m": "Уровень грунтовых вод",
    "freezing_depth_m": "Глубина промерзания",
    "liquid_temp_c": "Температура жидкости",
    "operating_mode": "Режим работы",
    "cycles_per_hour": "Циклы в час",
    "inflow_per_hour_m3": "Приток",
    "corpus_material": "Материал корпуса",
}


# Человеко-читаемые названия типов сточных вод (wastewater_type enum в L0).
# Применяется в reports/bom_pdf, rpz_gost, result_enrichment.
WASTEWATER_TYPE_LABELS = {
    "domestic": "хозяйственно-бытовые",
    "industrial": "промышленные",
    "drainage": "ливневые",
    "clean_water": "чистая вода",
    "fire_protection": "пожарные",
    "mixed": "смешанные",
}


def fmt_wastewater_type(wt: str | None) -> str:
    """Преобразует enum-ключ wastewater_type в человекочитаемое название.
    Пример: "domestic" → "хозяйственно-бытовые"."""
    if not wt:
        return "не указан"
    return WASTEWATER_TYPE_LABELS.get(wt, wt)


def fmt_l1_field(key: str | None) -> str:
    """Преобразует ключ L1-поля в человекочитаемое название.
    Пример: "L1.disinfection" → "Обеззараживание сточных вод".
    Если key начинается с "L1." — отрезает префикс."""
    if not key:
        return ""
    pure = key.removeprefix("L1.") if key.startswith("L1.") else key
    return L1_FIELD_LABELS.get(pure, pure)
