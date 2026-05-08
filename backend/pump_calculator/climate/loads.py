"""Расчёт климатических нагрузок на павильон КНС/ВНС.

Источники:
- СП 20.13330.2016 + Изм.№4 (2024) — снег (§10), ветер (§11)
- СП 14.13330.2018 + ОСР-2015 — сейсмика
"""
from __future__ import annotations

# СП 20.13330.2016 табл. 10.1 — нормативная снеговая нагрузка по районам, кПа.
SNOW_REGION_S0_KPA: dict[int, float] = {
    1: 0.8,
    2: 1.2,
    3: 1.8,
    4: 2.4,
    5: 3.2,
    6: 4.0,
    7: 4.8,
    8: 5.6,
}

# СП 20.13330.2016 табл. 11.1 — нормативное ветровое давление w_0, Па.
WIND_REGION_W0_PA: dict[int, int] = {
    1: 170,
    2: 230,
    3: 300,
    4: 380,
    5: 480,
    6: 600,
    7: 730,
    1.5: 200,    # Iа
}

# Снеговые районы для типовых городов (СП 20 карта 1)
CITY_TO_SNOW_REGION: dict[str, int] = {
    "Краснодар": 2,
    "Сочи": 2,
    "Ростов-на-Дону": 2,
    "Симферополь": 1,
    "Москва": 3,
    "Санкт-Петербург": 3,
    "Калининград": 3,
    "Воронеж": 3,
    "Казань": 4,
    "Уфа": 5,
    "Екатеринбург": 4,
    "Челябинск": 4,
    "Новосибирск": 4,
    "Красноярск": 4,
    "Иркутск": 3,
    "Магадан": 6,
    "Норильск": 5,
    "Якутск": 2,
    "Анадырь": 5,
    "Петропавловск-Камчатский": 7,
    "Хабаровск": 3,
    "Владивосток": 2,
}

# Ветровые районы (СП 20 карта 3)
CITY_TO_WIND_REGION: dict[str, int] = {
    "Краснодар": 4,
    "Сочи": 4,
    "Ростов-на-Дону": 3,
    "Симферополь": 3,
    "Москва": 1,
    "Санкт-Петербург": 2,
    "Калининград": 2,
    "Воронеж": 2,
    "Казань": 2,
    "Екатеринбург": 1,
    "Новосибирск": 3,
    "Красноярск": 3,
    "Хабаровск": 4,
    "Владивосток": 5,
    "Магадан": 5,
    "Анадырь": 7,
    "Петропавловск-Камчатский": 7,
}

# Коэффициенты сейсмичности (СП 14.13330 табл. 5.3 — упрощённо).
SEISMIC_COEFFICIENTS: dict[int, float] = {
    6: 0.025,   # МПа сейсмика, можно игнорировать для лёгких объектов
    7: 0.05,
    8: 0.10,
    9: 0.20,
    10: 0.40,
}


def _get_region_for_city(city: str, region_map: dict, default: int = 3) -> tuple[int, str]:
    """Определяет район для города из карты, либо возвращает default."""
    if city in region_map:
        return region_map[city], f"СП 20 для '{city}'"
    for known_city, region in region_map.items():
        if city.lower() in known_city.lower() or known_city.lower() in city.lower():
            return region, f"Найдено по совпадению с '{known_city}'"
    return default, f"Город '{city}' не найден, fallback район {default}"


def calc_snow_load_pavilion(
    region_city: str,
    pavilion_area_m2: float,
    roof_shape: str = "flat",
) -> tuple[float, float, str, list[str]]:
    """Расчёт снеговой нагрузки на павильон.

    Формула СП 20.13330 §10.1:
        S = S_0 × μ × c_e × c_t

    Где:
    - S_0 — нормативное значение по району (табл. 10.1)
    - μ — коэф. формы крыши (для плоской 0.85-1.0)
    - c_e, c_t — коэф. условий (упрощённо = 1.0)
    """
    region, source = _get_region_for_city(region_city, CITY_TO_SNOW_REGION, default=3)
    s_0 = SNOW_REGION_S0_KPA.get(region, 1.8)

    # Коэффициент формы крыши
    mu_map = {
        "flat": 1.0,
        "single_pitch": 0.85,
        "double_pitch": 0.75,
    }
    mu = mu_map.get(roof_shape, 1.0)

    # S = S_0 × μ × c_e × c_t (c_e = c_t = 1.0)
    s = s_0 * mu

    s_total_kn = s * pavilion_area_m2  # кН (т.к. кПа·м² = кН)

    notes = [
        f"Район снеговой нагрузки: {region} ({source})",
        f"S_0 = {s_0} кПа (СП 20 табл. 10.1)",
        f"μ = {mu} (форма крыши '{roof_shape}')",
        f"S = S_0 × μ = {s:.2f} кПа",
        f"S_общ = {s_total_kn:.1f} кН (на крыше {pavilion_area_m2} м²)",
    ]
    return s, s_total_kn, f"район {region}", notes


def calc_wind_load_pavilion(
    region_city: str,
    pavilion_height_m: float,
    pavilion_facade_area_m2: float,
) -> tuple[float, float, str, list[str]]:
    """Расчёт ветровой нагрузки на фасад павильона.

    Формула СП 20.13330 §11.1:
        w_m = w_0 × k(z) × c

    Где:
    - w_0 — нормативное давление по району (табл. 11.1)
    - k(z) — коэф. высоты (для z=10м k=1.0; формулы СП 20 §11.1.5)
    - c — аэродинамический (для павильона ≈ 0.8 на наветренной)
    """
    region, source = _get_region_for_city(region_city, CITY_TO_WIND_REGION, default=2)
    w_0 = WIND_REGION_W0_PA.get(region, 230)

    # k(z) для типа местности B (тип B — застройка) при z<10 м
    if pavilion_height_m <= 5:
        k_z = 0.5
    elif pavilion_height_m <= 10:
        k_z = 0.65
    else:
        k_z = 0.85

    # c — на наветренную (упрощённо)
    c = 0.8

    w_m = w_0 * k_z * c
    w_total_kn = w_m * pavilion_facade_area_m2 / 1000.0  # Па·м² = Н, → кН

    notes = [
        f"Ветровой район: {region} ({source})",
        f"w_0 = {w_0} Па (СП 20 табл. 11.1)",
        f"k(z) = {k_z} (высота {pavilion_height_m} м, тип местности B)",
        f"c = {c} (аэродинамический, наветренная)",
        f"w_m = w_0 × k × c = {w_m:.0f} Па",
        f"W_общ = {w_total_kn:.1f} кН (фасад {pavilion_facade_area_m2:.1f} м²)",
    ]
    return w_m, w_total_kn, f"район {region}", notes


def calc_seismic_load(
    seismic_intensity_balls: int,
    object_mass_kg: float,
) -> tuple[float, float, list[str]]:
    """Сейсмическая горизонтальная сила.

    F_сейсм = K × m × g
    K — коэффициент по интенсивности (табл. 5.3 СП 14)
    """
    K = SEISMIC_COEFFICIENTS.get(seismic_intensity_balls, 0.0)
    F_kn = K * object_mass_kg * 9.81 / 1000.0

    if seismic_intensity_balls < 7:
        notes = [
            f"Интенсивность {seismic_intensity_balls} баллов — расчёт не обязателен (СП 14 §5.1)",
        ]
    else:
        notes = [
            f"Интенсивность {seismic_intensity_balls} баллов",
            f"K_сейсм = {K} (СП 14 табл. 5.3 / ОСР-2015)",
            f"F = K × m × g = {K} × {object_mass_kg} × 9.81 = {F_kn:.2f} кН",
        ]

    return K, F_kn, notes
