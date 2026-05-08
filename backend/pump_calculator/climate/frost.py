"""Расчёт глубины промерзания и заложения трубы.

Источники:
- СП 131.13330.2020 — нормативная глубина промерзания d_fn по городам
- СП 32.13330.2018 §6.5 — заложение сетей канализации
- СП 25.13330.2020 — вечномёрзлые грунты

Формула:
    d_pipe = d_fn × k_h + 0.3 (СП 32 §6.5: ниже глубины промерзания на 0.3 м)
    d_fn — нормативное промерзание (для глины/суглинка)
    k_h — коэффициент по типу грунта (1.2 для песка, 0.8 для скалы)
"""
from __future__ import annotations

# СП 131.13330.2020 табл. 5.1 — нормативная глубина сезонного промерзания (м)
# для глины и суглинка. Для других грунтов умножить на k_h (см. SOIL_FROST_FACTORS).
FROST_DEPTH_BY_CITY_M: dict[str, float] = {
    # Юг РФ
    "Краснодар":        0.8,
    "Сочи":             0.0,    # без промерзания
    "Ростов-на-Дону":   0.9,
    "Симферополь":      0.7,
    "Ялта":             0.5,
    "Ставрополь":       0.8,
    "Махачкала":        0.6,
    "Владикавказ":      0.9,
    # Центр и Северо-Запад
    "Москва":           1.4,
    "Санкт-Петербург":  1.2,
    "Воронеж":          1.4,
    "Тула":             1.4,
    "Калуга":           1.4,
    "Тверь":            1.4,
    "Псков":            1.2,
    "Великий Новгород": 1.3,
    "Калининград":      1.0,
    # Поволжье и Урал
    "Нижний Новгород":  1.5,
    "Казань":           1.7,
    "Самара":           1.6,
    "Саратов":          1.5,
    "Уфа":              1.8,
    "Пермь":            1.8,
    "Екатеринбург":     1.8,
    "Челябинск":        1.9,
    # Сибирь
    "Тюмень":           2.0,
    "Омск":             2.2,
    "Новосибирск":      2.2,
    "Красноярск":       2.2,
    "Иркутск":          2.6,
    "Норильск":         3.0,
    # Дальний Восток
    "Хабаровск":        2.0,
    "Владивосток":      1.6,
    "Якутск":           3.0,
    "Магадан":          2.5,
    "Петропавловск-Камчатский": 1.5,
    "Анадырь":          3.0,
}

# Коэффициенты грунта (СП 22.13330 табл. 5.3 для расчёта d_f).
# d_f = d_fn × k_h. Для песка/гравия глубина больше, для скалы меньше.
SOIL_FROST_FACTORS: dict[str, float] = {
    "sand_dry":   1.30,    # Пески крупные, гравелистые сухие
    "sand_wet":   1.20,    # Пески водонасыщенные
    "clay_loam":  1.00,    # Суглинки (базовая)
    "clay":       0.90,    # Глины
    "rocky":      0.70,    # Скальные грунты
    "peat":       1.50,    # Торф, органика — самые подверженные
}


def calc_frost_depth_normative(region_city: str) -> tuple[float, str]:
    """Возвращает нормативную глубину промерзания d_fn для города.

    Если города нет в БД — возвращает 1.5 (среднее по РФ) с предупреждением.
    """
    if region_city in FROST_DEPTH_BY_CITY_M:
        return FROST_DEPTH_BY_CITY_M[region_city], f"Из СП 131 для '{region_city}'"
    # Поиск по подстроке (Москва Санкт-Петербург и т.п.)
    for city, depth in FROST_DEPTH_BY_CITY_M.items():
        if region_city.lower() in city.lower() or city.lower() in region_city.lower():
            return depth, f"Найдено по совпадению с '{city}'"
    return 1.5, f"Город '{region_city}' не найден в БД, fallback 1.5 м (среднее по РФ)"


def calc_pipe_burial_depth(
    region_city: str,
    soil_type: str = "clay_loam",
    pipe_dn_mm: float = 200,
    has_groundwater: bool = False,
):
    """Расчёт глубины заложения канализационного трубопровода.

    СП 32.13330.2018 §6.5: глубина заложения должна быть не менее d_f + 0.3 м
    для труб DN ≤ 500 мм и d_f + 0.5 м для DN > 500.

    Args:
        region_city: город из БД промерзания
        soil_type: тип грунта (для коэф. k_h)
        pipe_dn_mm: диаметр трубы
        has_groundwater: высокий УГВ — добавляет +0.2 м запас
    """
    from .models import PipeBurialResult

    d_fn, source = calc_frost_depth_normative(region_city)
    k_h = SOIL_FROST_FACTORS.get(soil_type, 1.0)
    d_f = d_fn * k_h

    # Запас по СП 32 §6.5
    if pipe_dn_mm > 500:
        margin = 0.5
        margin_note = "DN>500 → +0.5 м (СП 32 §6.5)"
    else:
        margin = 0.3
        margin_note = "DN≤500 → +0.3 м (СП 32 §6.5)"

    burial = d_f + margin

    notes = [
        f"d_fn = {d_fn} м ({source})",
        f"k_h = {k_h} (грунт: {soil_type})",
        f"d_f = d_fn × k_h = {d_f:.2f} м",
        margin_note,
        f"d_заложения = {burial:.2f} м",
    ]

    # Утепление если глубина заложения < d_f (для южных регионов часто экономически
    # выгоднее утеплять, чем закапывать на 1.5+ м)
    insulation_required = False
    insulation_thickness = 0.0
    if has_groundwater and burial > 2.5:
        insulation_required = True
        insulation_thickness = 100.0
        notes.append("УГВ высокий + d>2.5 м → рекомендуется утепление 100 мм минваты")
    elif d_fn > 2.0:
        insulation_required = True
        insulation_thickness = 50 if d_fn < 2.5 else 100
        notes.append(f"d_fn={d_fn} м (Сибирь) → утепление {insulation_thickness} мм")

    references = [
        {
            "regulation_code": "СП 32.13330.2018",
            "section": "§6.5",
            "purpose": "Глубина заложения сетей канализации",
            "url": "https://docs.cntd.ru/document/554820821",
        },
        {
            "regulation_code": "СП 131.13330.2020",
            "section": "табл. 5.1",
            "purpose": "Нормативная глубина промерзания по городам",
            "url": "https://docs.cntd.ru/document/573659358",
        },
    ]

    return PipeBurialResult(
        burial_depth_m=round(burial, 2),
        frost_depth_normative_m=d_fn,
        frost_depth_actual_m=round(d_f, 2),
        insulation_required=insulation_required,
        insulation_thickness_mm=insulation_thickness,
        notes=notes,
        references=references,
    )
