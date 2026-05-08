"""Расчёт водопотребления по СП 30.13330.2020 + СП 31.13330.2021.

Норма потребления — табл. А.2 СП 30 (для жилья), приложение Б (общественные).
Коэффициенты неравномерности — табл. 1, 2 СП 31 §5.

Главные формулы:
    Q_сред = N · q / 1000   (м³/сут)
    Q_max_сут = K_сут_max × Q_сред   (СП 31 §5.2: K=1.1-1.3)
    Q_max_час = (Q_max_сут / 24) × K_час_max   (К_час по табл. 2 СП 31)
    Q_max_сек = Q_max_час · 1000 / 3600   (л/с)
"""
from __future__ import annotations

from .models import (
    BuildingType,
    Q_aggregate,
    WaterDemandResult,
    WaterScenarioInput,
)

# Нормы суточного водопотребления по СП 30.13330.2020 прил. А.2 + прил. Б
# (л/(ед·сут), общая = ХВС + ГВС, для ГВС обычно 30-50% общей).
NORMS_LITERS_PER_DAY: dict[BuildingType, dict] = {
    "residential_with_baths":   {"unit": "чел", "norm_total": 250, "norm_hot": 105, "K_sut_max": 1.2, "K_hour_max": 1.4},
    "residential_with_showers": {"unit": "чел", "norm_total": 200, "norm_hot": 85,  "K_sut_max": 1.2, "K_hour_max": 1.5},
    "residential_no_baths":     {"unit": "чел", "norm_total": 110, "norm_hot": 50,  "K_sut_max": 1.3, "K_hour_max": 1.7},
    "hotel_high_class":         {"unit": "номер", "norm_total": 300, "norm_hot": 130, "K_sut_max": 1.2, "K_hour_max": 1.5},
    "hotel_standard":           {"unit": "номер", "norm_total": 230, "norm_hot": 100, "K_sut_max": 1.2, "K_hour_max": 1.6},
    "hostel":                   {"unit": "место", "norm_total": 130, "norm_hot": 60,  "K_sut_max": 1.2, "K_hour_max": 1.7},
    "office":                   {"unit": "чел", "norm_total": 16,  "norm_hot": 7,   "K_sut_max": 1.0, "K_hour_max": 2.5},
    "school":                   {"unit": "учащийся", "norm_total": 11, "norm_hot": 4, "K_sut_max": 1.0, "K_hour_max": 3.0},
    "kindergarten":             {"unit": "место", "norm_total": 75, "norm_hot": 30, "K_sut_max": 1.0, "K_hour_max": 2.0},
    "hospital":                 {"unit": "койка", "norm_total": 250, "norm_hot": 100, "K_sut_max": 1.0, "K_hour_max": 2.5},
    "polyclinic":               {"unit": "посещение", "norm_total": 13, "norm_hot": 5, "K_sut_max": 1.0, "K_hour_max": 3.0},
    "shop":                     {"unit": "100м²", "norm_total": 8, "norm_hot": 3, "K_sut_max": 1.0, "K_hour_max": 1.5},
    "trc":                      {"unit": "100м²", "norm_total": 12, "norm_hot": 4, "K_sut_max": 1.0, "K_hour_max": 1.5},
    "restaurant":               {"unit": "посетитель", "norm_total": 12, "norm_hot": 5, "K_sut_max": 1.0, "K_hour_max": 1.5},
    "sports":                   {"unit": "посетитель", "norm_total": 50, "norm_hot": 30, "K_sut_max": 1.0, "K_hour_max": 1.5},
    "swimming_pool":            {"unit": "посетитель", "norm_total": 100, "norm_hot": 60, "K_sut_max": 1.0, "K_hour_max": 1.5},
    "bathhouse":                {"unit": "посетитель", "norm_total": 180, "norm_hot": 120, "K_sut_max": 1.0, "K_hour_max": 1.4},
    "laundry":                  {"unit": "кг", "norm_total": 75, "norm_hot": 25, "K_sut_max": 1.0, "K_hour_max": 1.3},
    "carwash":                  {"unit": "авто", "norm_total": 250, "norm_hot": 50, "K_sut_max": 1.0, "K_hour_max": 1.5},
    "industrial_generic":       {"unit": "чел", "norm_total": 25, "norm_hot": 11, "K_sut_max": 1.0, "K_hour_max": 2.0},
    "agricultural":             {"unit": "голова", "norm_total": 60, "norm_hot": 0, "K_sut_max": 1.0, "K_hour_max": 2.5},
}


def _resolve_n_units(inputs: WaterScenarioInput) -> int:
    """Определяет число расчётных единиц по типу здания."""
    bt = inputs.building_type
    norm = NORMS_LITERS_PER_DAY[bt]
    unit = norm["unit"]

    if unit == "чел" or unit == "место" or unit == "учащийся":
        return inputs.population
    if unit == "номер":
        return inputs.rooms
    if unit == "койка":
        return inputs.beds
    if unit == "посещение" or unit == "посетитель":
        return inputs.visits_per_day
    if unit == "100м²":
        return int(inputs.area_m2 / 100)  # на 100 м²
    if unit == "кг" or unit == "авто":
        return inputs.visits_per_day or inputs.population
    if unit == "голова":
        return inputs.population
    return inputs.population  # fallback


def _calc_aggregate(
    n_units: int,
    norm_l: float,
    K_sut: float,
    K_hour: float,
    unit: str,
) -> Q_aggregate:
    """Агрегированные расходы из нормы и числа единиц."""
    Q_avg_m3 = n_units * norm_l / 1000.0       # м³/сут
    Q_max_day_m3 = Q_avg_m3 * K_sut            # м³/сут
    Q_max_hour_m3h = Q_max_day_m3 / 24.0 * K_hour
    Q_max_sec_lps = Q_max_hour_m3h * 1000.0 / 3600.0
    return Q_aggregate(
        Q_avg_m3_per_day=round(Q_avg_m3, 2),
        Q_max_day_m3=round(Q_max_day_m3, 2),
        Q_max_hour_m3h=round(Q_max_hour_m3h, 2),
        Q_max_sec_lps=round(Q_max_sec_lps, 3),
        K_sut_max=K_sut,
        K_hour_max=K_hour,
        norm_l_per_unit_day=norm_l,
        unit=unit,
        n_units=n_units,
    )


def calc_water_demand(inputs: WaterScenarioInput) -> WaterDemandResult:
    """Полный расчёт водопотребления для объекта.

    Возвращает раздельно: cold_water, hot_water (если есть), irrigation (если есть),
    суммарные показатели и ссылки на нормативы.
    """
    bt = inputs.building_type
    if bt not in NORMS_LITERS_PER_DAY:
        raise ValueError(f"Unknown building_type: {bt}")
    norm = NORMS_LITERS_PER_DAY[bt]

    n_units = _resolve_n_units(inputs)
    notes: list[str] = []

    if n_units <= 0:
        raise ValueError(
            f"Не задано число расчётных единиц для типа '{bt}' "
            f"(unit='{norm['unit']}'). Установите population/rooms/beds/visits_per_day/area_m2."
        )

    # Холодная вода — норма total минус hot (если есть ГВС)
    norm_cold = norm["norm_total"] - (norm["norm_hot"] if inputs.has_hot_water else 0)
    cold = _calc_aggregate(
        n_units=n_units,
        norm_l=norm_cold,
        K_sut=norm["K_sut_max"],
        K_hour=norm["K_hour_max"],
        unit=norm["unit"],
    )
    notes.append(
        f"Холодная вода: {n_units} {norm['unit']} × {norm_cold} л/сут = {cold.Q_avg_m3_per_day} м³/сут"
    )

    # Горячая вода (если есть)
    hot = None
    if inputs.has_hot_water and norm["norm_hot"] > 0:
        hot = _calc_aggregate(
            n_units=n_units,
            norm_l=norm["norm_hot"],
            K_sut=norm["K_sut_max"],
            K_hour=norm["K_hour_max"],
            unit=norm["unit"],
        )
        notes.append(
            f"Горячая вода: {n_units} {norm['unit']} × {norm['norm_hot']} л/сут = {hot.Q_avg_m3_per_day} м³/сут"
        )

    # Полив (3 л/м²·сут по СП 30 прил. А)
    irrigation = None
    if inputs.has_irrigation and inputs.irrigation_area_m2 > 0:
        Q_irr_avg = inputs.irrigation_area_m2 * 3.0 / 1000.0  # м³/сут
        # Полив только в тёплое время — но для расчёта берём как пиковое
        irrigation = Q_aggregate(
            Q_avg_m3_per_day=round(Q_irr_avg, 2),
            Q_max_day_m3=round(Q_irr_avg, 2),
            Q_max_hour_m3h=round(Q_irr_avg / 4.0, 2),  # за 4 часа полив
            Q_max_sec_lps=round(Q_irr_avg * 1000.0 / 4.0 / 3600.0, 3),
            K_sut_max=1.0,
            K_hour_max=1.0,
            norm_l_per_unit_day=3.0,
            unit="м² газона",
            n_units=int(inputs.irrigation_area_m2),
        )
        notes.append(
            f"Полив: {inputs.irrigation_area_m2:.0f} м² × 3 л/м² = {Q_irr_avg:.2f} м³/сут"
        )

    # Суммарные
    total_avg = cold.Q_avg_m3_per_day + (hot.Q_avg_m3_per_day if hot else 0) + (irrigation.Q_avg_m3_per_day if irrigation else 0)
    total_max_day = cold.Q_max_day_m3 + (hot.Q_max_day_m3 if hot else 0) + (irrigation.Q_max_day_m3 if irrigation else 0)
    total_max_hour = cold.Q_max_hour_m3h + (hot.Q_max_hour_m3h if hot else 0) + (irrigation.Q_max_hour_m3h if irrigation else 0)
    total_max_sec = cold.Q_max_sec_lps + (hot.Q_max_sec_lps if hot else 0) + (irrigation.Q_max_sec_lps if irrigation else 0)

    references = [
        {
            "regulation_code": "СП 30.13330.2020",
            "section": "прил. А.2 + прил. Б",
            "purpose": "Нормы потребления холодной и горячей воды",
            "url": "https://docs.cntd.ru/document/573135590",
        },
        {
            "regulation_code": "СП 31.13330.2021",
            "section": "§5.2, табл. 1, 2",
            "purpose": "Коэф. суточной и часовой неравномерности",
            "url": "https://docs.cntd.ru/document/727733100",
        },
    ]

    return WaterDemandResult(
        cold_water=cold,
        hot_water=hot,
        irrigation=irrigation,
        total_Q_avg_m3_day=round(total_avg, 2),
        total_Q_max_day_m3=round(total_max_day, 2),
        total_Q_max_hour_m3h=round(total_max_hour, 2),
        total_Q_max_sec_lps=round(total_max_sec, 3),
        references=references,
        notes=notes,
    )
