"""Состав стоков и ПДК для разных категорий сброса.

Источники:
- ПП РФ №728 от 13.07.2013, прил. 5 (центральная канализация)
- СанПиН 2.1.5.980-00 (хозпитьевой / питьевой)
- Приказ МСХ-552 от 13.12.2016 (рыбохозяйственный)
- ИТС 10-2015 НДТ
"""
from __future__ import annotations

from .models import (
    DischargeCategory,
    PollutantConcentration,
    SourceType,
)

# Типовой состав хозбытовых стоков (на входе ЛОС, мг/л)
TYPICAL_INFLUENT_DOMESTIC = PollutantConcentration(
    bod5=250,
    cod=550,
    suspended_solids=250,
    nh4_n=40,
    po4_p=10,
    surfactants=8,
    fats=70,
    ph=7.2,
)

TYPICAL_INFLUENT_INDUSTRIAL_FOOD = PollutantConcentration(
    bod5=2500,
    cod=4000,
    suspended_solids=600,
    nh4_n=80,
    po4_p=25,
    fats=600,
    ph=6.5,
)

TYPICAL_INFLUENT_INDUSTRIAL_OILY = PollutantConcentration(
    bod5=300,
    cod=800,
    suspended_solids=400,
    oil_products=200,
    surfactants=15,
    ph=7.5,
)

TYPICAL_INFLUENT_STORMWATER = PollutantConcentration(
    bod5=20,
    cod=80,
    suspended_solids=200,    # SS высокий — нужны песко- и нефтеуловители
    oil_products=15,         # Дождевые с дорог содержат нефтепродукты
    ph=7.5,
)

TYPICAL_INFLUENT_LEACHATE = PollutantConcentration(
    bod5=15000,
    cod=40000,
    suspended_solids=2000,
    nh4_n=2500,        # Очень высокий — ключевая проблема фильтрата ТКО
    po4_p=80,
    ph=8.0,
)


def typical_influent_for_object(source: SourceType) -> PollutantConcentration:
    """Возвращает типовой состав стоков по типу объекта."""
    match source:
        case "domestic":
            return TYPICAL_INFLUENT_DOMESTIC
        case "industrial_food":
            return TYPICAL_INFLUENT_INDUSTRIAL_FOOD
        case "industrial_oily":
            return TYPICAL_INFLUENT_INDUSTRIAL_OILY
        case "stormwater":
            return TYPICAL_INFLUENT_STORMWATER
        case "leachate_landfill":
            return TYPICAL_INFLUENT_LEACHATE
        case _:
            return TYPICAL_INFLUENT_DOMESTIC


# ПДК для сброса в разные категории водоприёмников
# Все значения в мг/л (кроме pH)
POLLUTANT_LIMITS_BY_DISCHARGE: dict[DischargeCategory, dict[str, float]] = {
    "central_sewerage": {
        # ПП РФ №728 прил. 5 — мягкие требования
        "bod5": 300,
        "cod": 500,
        "suspended_solids": 300,
        "ph_min": 6.5, "ph_max": 9.0,
        "oil_products": 10,
        "fats": 50,
        "surfactants": 20,
        "nh4_n": 50,
        "po4_p": 12,
    },
    "household_source": {
        # СанПиН 2.1.5.980-00, II категория водоёмов
        "bod5": 6.0,
        "cod": 30,
        "suspended_solids": 0.75,
        "oil_products": 0.3,
        "nh4_n": 2.0,
        "ph_min": 6.5, "ph_max": 8.5,
    },
    "drinking_source": {
        # СанПиН 2.1.5.980-00, I категория — самые строгие для пресной питьевой
        "bod5": 3.0,
        "cod": 15,
        "suspended_solids": 0.25,
        "oil_products": 0.1,
        "nh4_n": 1.5,
        "ph_min": 6.5, "ph_max": 8.5,
    },
    "fishery_water": {
        # Приказ МСХ-552 — рыбохозяйственный, самые строгие
        "bod5": 2.1,         # БПК полн ≤ 3.0
        "cod": 15,
        "suspended_solids": 0.25,
        "oil_products": 0.05,
        "nh4_n": 0.39,       # рыбхоз. ПДК
        "no3_n": 9.1,
        "po4_p": 0.2,
        "surfactants": 0.1,
        "ph_min": 6.5, "ph_max": 8.5,
    },
    "ground_water": {
        # Поглощающие колодцы — близко к питьевой норме
        "bod5": 5,
        "cod": 30,
        "suspended_solids": 5,
        "oil_products": 0.3,
        "nh4_n": 2.0,
    },
    "irrigation": {
        # Полив — менее строго, главное гигиена
        "bod5": 30,
        "cod": 100,
        "suspended_solids": 30,
        "oil_products": 1.0,
    },
}


def calc_purification_efficiency(
    influent: PollutantConcentration,
    discharge_category: DischargeCategory,
) -> dict[str, float]:
    """Требуемая степень очистки η = (C_in - C_out) / C_in × 100%.

    Returns:
        Словарь {показатель: % очистки}, который нужно обеспечить.
    """
    limits = POLLUTANT_LIMITS_BY_DISCHARGE[discharge_category]
    result = {}
    for param, c_limit in limits.items():
        if param.startswith("ph"):
            continue
        c_in = getattr(influent, param, 0)
        if c_in <= 0 or c_in <= c_limit:
            result[param] = 0.0
            continue
        eta = (c_in - c_limit) / c_in * 100
        result[param] = round(eta, 1)
    return result
