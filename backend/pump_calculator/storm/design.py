"""Расчётные суточные объёмы для очистных (СП 32.13330.2018 п. 6.4.5).

Главные формулы:
    h_a = H_cp × (1 + C_v × Φ)  — слой расч. дождя
    W_д_сут = 10 × h_a × ψ_mid × F  — суточный объём для очистных
    W_т_сут = 10 × ψ_T × α × F × K_y × h_c
"""
from __future__ import annotations

from .models import DesignVolumes, StormInput
from .surfaces import calc_psi_design, surfaces_from_breakdown

# Φ для P=63% (среднегодовое) при C_s = 2 × C_v — стандартное допущение СП 33-101-2003
_PHI_P63_DEFAULT = -0.32


def calc_h_a(H_cp_mm: float, Cv: float, Phi: float = _PHI_P63_DEFAULT) -> float:
    """Расчётный слой осадков, мм (СП 32 формула в прил. Е.6).

    h_a = H_cp × (1 + C_v × Φ)
    """
    return H_cp_mm * (1.0 + Cv * Phi)


def calc_h_c_typical(region: dict) -> float:
    """Типовой слой стока талых вод за 10 дневных часов.

    Регион определяется по h_cold (тёплый период) и температуре наиболее холодной 5%.
    Это упрощение СП 32 прил. Г (полные изолинии нужно векторизовать с карты).
    """
    h_cold = region["h_cold_mm"]
    if h_cold <= 100:
        return 5.5  # юг
    if h_cold <= 200:
        return 15.0  # центр/Поволжье
    if h_cold <= 300:
        return 25.0  # СЗ/Урал
    return 35.0  # Сибирь/Север


def calculate_design_volume(inputs: StormInput, region: dict) -> DesignVolumes:
    """Расчётный суточный объём дождевых и талых для подбора ЛОС."""
    H_cp = region["Hcp_mm"]
    Cv = region["Cv"]

    # Расч. слой за расч. дождь (P=63% обеспеченности)
    h_a = calc_h_a(H_cp, Cv)

    # ψ_mid для дождевых (для очистных используются те же значения, что для расчёта стока)
    surfaces = surfaces_from_breakdown(inputs.surfaces)
    psi_mid, F_total_ha = calc_psi_design(surfaces, inputs.sp_revision)

    # Дождевые суточные
    W_d_design = 10 * h_a * psi_mid * F_total_ha

    # Талые суточные
    h_c = calc_h_c_typical(region)
    psi_t = 0.5
    alpha = 0.8 if region["h_cold_mm"] <= 200 else 1.0  # неравномерность таяния
    K_y = 1.0 - inputs.snow_clearance_pct
    W_t_design = 10 * psi_t * alpha * F_total_ha * K_y * h_c

    max_for_acc = max(W_d_design, W_t_design)

    return DesignVolumes(
        h_a_mm=round(h_a, 2),
        psi_mid=round(psi_mid, 4),
        rain_design_m3_day=round(W_d_design, 1),
        snowmelt_design_m3_day=round(W_t_design, 1),
        max_for_accumulator_m3=round(max_for_acc, 1),
    )
