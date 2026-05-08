"""Расчёт пикового расхода Q_r методом предельных интенсивностей (СП 32.13330.2018 §6.2.4).

Главная формула:
    Q_r = Z_mid × A^1.2 × F / t_r^(1.2n − 0.1)

Параметр A:
    A = q_20 × 20^n × (1 + lg(P)/lg(m_r))^γ

Время добегания:
    t_r = t_con + t_can + t_p
    t_p = 0.017 × Σ(L_p / v_p)
"""
from __future__ import annotations

import math

from .models import (
    LosRecommendation,
    PeakFlow,
    StormInput,
    StormResult,
)
from .regions import get_climate_params
from .surfaces import calc_z_mid, surfaces_from_breakdown

# γ показатель степени по табл. Б.4 СП 32 §6.2.4.
# Phase 18.2 (2026-05-08): γ берётся из climate_db_36_cities.json (поле "gamma"),
# для городов без поля используется этот fallback (центральная часть РФ).
# - Юг ЕТР, Кавказ, Крым, Дальний Восток (приморский климат): γ=1.82
# - Центр ЕТР, Поволжье, Урал, Сибирь, Северо-Запад: γ=1.54
_GAMMA_DEFAULT = 1.54


def calc_A(q20: float, n: float, P: int, mr: int, gamma: float = _GAMMA_DEFAULT) -> float:
    """Параметр A в формуле интенсивности дождя (СП 32 формула 8).

    A = q_20 × 20^n × (1 + lg(P)/lg(m_r))^γ
    """
    if P <= 0 or mr <= 1:
        raise ValueError(f"Invalid P={P} or mr={mr} (mr must be >1)")
    base = 1.0 + math.log10(P) / math.log10(mr)
    return q20 * (20 ** n) * (base ** gamma)


def calc_t_r(
    t_concentration_min: float,
    pipe_length_m: float,
    pipe_velocity_mps: float,
    t_canal_min: float = 0.0,
) -> tuple[float, float]:
    """Расчётное время дождя t_r (СП 32 формула 11).

    Returns:
        (t_r, t_p) — общее время и время в трубах.
    """
    t_p = 0.017 * pipe_length_m / pipe_velocity_mps if pipe_velocity_mps > 0 else 0.0
    t_r = t_concentration_min + t_canal_min + t_p
    return t_r, t_p


def calculate_peak_flow(inputs: StormInput) -> tuple[PeakFlow, dict]:
    """Расчёт пикового расхода Q_r."""
    region = get_climate_params(inputs.region_city)
    if region is None:
        raise ValueError(f"City '{inputs.region_city}' not found in climate DB")

    q20 = region["q20_l_s_ha"]
    n = region["n"]
    mr = region["mr"]
    # Phase 18.2: γ читается из БД, fallback на 1.54 (центральная РФ).
    gamma = region.get("gamma", _GAMMA_DEFAULT)

    # Параметры
    A = calc_A(q20, n, inputs.period_P_year, mr, gamma=gamma)
    surfaces = surfaces_from_breakdown(inputs.surfaces)
    Z_mid, F_total_ha = calc_z_mid(surfaces, inputs.sp_revision)

    if F_total_ha == 0:
        raise ValueError("Total area F = 0 — provide surfaces breakdown")

    t_r, t_p = calc_t_r(
        inputs.t_concentration_min,
        inputs.pipe_total_length_m,
        inputs.pipe_velocity_mps,
    )

    # Q_r = Z_mid × A^1.2 × F / t_r^(1.2n − 0.1)
    exp_t = 1.2 * n - 0.1
    Q_r = Z_mid * (A ** 1.2) * F_total_ha / (t_r ** exp_t)

    return (
        PeakFlow(
            Q_r_l_s=round(Q_r, 2),
            t_r_min=round(t_r, 2),
            t_p_min=round(t_p, 2),
            A_param=round(A, 2),
            Z_mid=round(Z_mid, 4),
        ),
        region,
    )


def calculate_full_storm(inputs: StormInput) -> StormResult:
    """Полный расчёт ливневой системы для калькулятора."""
    from .annual import calculate_annual_volumes
    from .design import calculate_design_volume

    peak, region = calculate_peak_flow(inputs)
    annual = calculate_annual_volumes(inputs, region)
    design = calculate_design_volume(inputs, region)

    # Рекомендация по ЛОС: накопитель = расч. суточный, мощность = от Q_r/24 до Q_r
    accumulator_v = design.max_for_accumulator_m3 if inputs.selective_treatment else (
        design.max_for_accumulator_m3 + 50  # +20% для байпаса условно-чистой
    )
    los_min = round(design.max_for_accumulator_m3 / 86.4, 2)  # м³/24ч → л/с
    los_max = round(peak.Q_r_l_s, 2)

    warnings = []
    if peak.Q_r_l_s > 1000:
        warnings.append(
            f"Очень большой пиковый расход {peak.Q_r_l_s} л/с — потребуется крупная КНС "
            f"с РЧВ или каскадная схема"
        )
    if peak.Q_r_l_s < 5:
        warnings.append(
            f"Малый расход {peak.Q_r_l_s} л/с — возможно достаточно самотёчной схемы без КНС"
        )

    formula_ref_str = (
        "СП 32.13330.2012 табл.14 (Q_r формула 8)"
        if inputs.sp_revision == "SP_32_2012"
        else "СП 32.13330.2018 §6.2.4 + прил. Б.2"
    )

    return StormResult(
        annual=annual,
        design=design,
        peak=peak,
        recommendation=LosRecommendation(
            accumulator_volume_m3=round(accumulator_v, 1),
            los_capacity_l_s_min=los_min,
            los_capacity_l_s_max=los_max,
            bypass_for_clean=inputs.selective_treatment,
        ),
        sp_revision_used=inputs.sp_revision,
        formula_ref=formula_ref_str,
        tolerance_pct=15.0,
        warnings=warnings,
        region_data=region,
        inputs_summary={
            "city": inputs.region_city,
            "F_total_ha": round(inputs.surfaces.total_ha, 2),
            "P_year": inputs.period_P_year,
            "sp_revision": inputs.sp_revision,
        },
    )
