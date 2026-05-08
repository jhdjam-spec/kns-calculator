"""Полный сценарий расчёта пожарного водоснабжения для одного объекта.

Объединяет:
- расход на наружное (СП 8.13130)
- расход на внутреннее (СП 10.13130)
- расход спринклеров (СП 485)
- объём резервуара (СП 8.13130 §9)
- подбор насосной станции (СП 8.13130 §10, СП 10.13130 §6)
"""
from __future__ import annotations

from ..regulations import ref
from .external import calc_external_demand
from .internal import calc_internal_demand
from .models import FireDemand, FireResult, FireScenarioInput, RegulationRefDict
from .pump_station import sizing_fire_pump_station
from .reservoir import sizing_reservoir


def _to_ref_dict(r) -> RegulationRefDict:
    return RegulationRefDict(
        regulation_code=r.regulation_code,
        section=r.section,
        purpose=r.purpose,
        quote=r.quote,
        url=r.url,
    )


def calculate_fire_scenario(
    inputs: FireScenarioInput,
    H_design_m: float = 60.0,
) -> FireResult:
    """Полный расчёт противопожарного водоснабжения для здания/комплекса."""
    warnings: list[str] = []

    # 1. Наружное (СП 8.13130)
    q_ext_lps, ext_table_ref, ext_notes = calc_external_demand(inputs)

    # 2. Внутреннее (СП 10.13130)
    q_int_lps, int_notes = calc_internal_demand(inputs)

    # 3. Спринклеры (введены пользователем)
    q_spr_lps = inputs.sprinkler_flow_lps

    # Суммарный расход (расчётный для насосной)
    q_total_lps = q_ext_lps + q_int_lps + q_spr_lps
    q_total_m3h = q_total_lps * 3.6

    demand = FireDemand(
        external_lps=round(q_ext_lps, 2),
        internal_lps=round(q_int_lps, 2),
        sprinkler_lps=round(q_spr_lps, 2),
        total_lps=round(q_total_lps, 2),
        total_m3h=round(q_total_m3h, 2),
        source_table=ext_table_ref,
    )

    # 4. Резервуар (если источник — резервуар)
    reservoir = None
    res_notes: list[str] = []
    if inputs.water_source == "reservoir":
        reservoir, res_notes = sizing_reservoir(inputs, demand)
    elif inputs.water_source == "city_network":
        warnings.append(
            "Источник — городская сеть. Требуется акт водоотдачи от МУП Водоканал "
            f"с подтверждением Q≥{q_total_lps:.1f} л/с при свободном напоре ≥10 м."
        )

    # 5. Насосная станция
    pump_station, ps_notes = sizing_fire_pump_station(inputs, demand, H_design_m)

    # 6. Сборка ссылок на нормативы (всегда возвращаем — режим энциклопедии)
    raw_refs = [
        ref("FZ_123", "ст. 32, 62", "Категории зданий и время пожаротушения"),
        ref("SP_8_13130", "табл. 1, 2", "Расход на наружное пожаротушение"),
        ref("SP_10_13130", "табл. 1, 2", "Расход на внутреннее пожаротушение"),
        ref("SP_8_13130", "§6.6", "Категория надёжности электроснабжения"),
        ref("SP_8_13130", "§9", "Расчёт пожарного резервуара"),
        ref("SP_10_13130", "§6.2", "Резервирование насосов 1+1"),
    ]

    if q_spr_lps > 0:
        raw_refs.append(
            ref("SP_5_13130", "табл. 5", "Автоматические установки пожаротушения")
        )

    references = [_to_ref_dict(r) for r in raw_refs]

    # Доп. предупреждения
    if inputs.height_m >= 17 and not inputs.has_internal_system:
        warnings.append(
            "Высота здания ≥17 м (СП 10.13130 §4) — проверьте обязательность ВПВ. "
            "В текущем расчёте принято: ВПВ требуется."
        )
    if inputs.fire_duration_h < 3.0 and inputs.occupancy != "residential":
        warnings.append(
            f"T_пож={inputs.fire_duration_h} ч меньше типового 3 ч — проверьте "
            f"по СП 8.13130 §6.3 (для не-жилых обычно ≥3 ч)."
        )

    return FireResult(
        demand=demand,
        reservoir=reservoir,
        pump_station=pump_station,
        references=references,
        warnings=warnings,
        inputs_echo=inputs,
    )
