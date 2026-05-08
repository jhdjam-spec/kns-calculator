"""Среднегодовые объёмы стоков (СП 32.13330.2018 п. 6.2.5, 6.2.9, 6.2.11)."""
from __future__ import annotations

from .models import AnnualVolumes, StormInput
from .surfaces import calc_psi_d_mid, surfaces_from_breakdown


def calculate_annual_volumes(inputs: StormInput, region: dict) -> AnnualVolumes:
    """Расчёт W_д, W_т, W_M, W_общ за год.

    Формулы:
        W_д = 10 × hд × ψд × F (м³/год)
        W_т = 10 × hт × 0.6 × F (м³/год)
        W_M = 10 × m × k × F_M × ψ_M (м³/год)
    """
    h_warm = region["h_warm_mm"]
    h_cold = region["h_cold_mm"]

    surfaces = surfaces_from_breakdown(inputs.surfaces)
    psi_d, F_total_ha = calc_psi_d_mid(surfaces, inputs.sp_revision)
    F_paved_ha = (
        inputs.surfaces.roof_ha
        + inputs.surfaces.asphalt_ha
        + inputs.surfaces.paving_dense_ha
        + inputs.surfaces.paving_loose_ha
    )

    # Дождевые
    W_d = 10 * h_warm * psi_d * F_total_ha

    # Талые (psi_T = 0.6 default)
    psi_t = 0.6
    W_t = 10 * h_cold * psi_t * F_total_ha

    # Поливомоечные (только для твёрдых покрытий)
    # m = 1.3 л/м² (среднее), k зависит от региона
    h_warm_int = int(h_warm)
    if h_warm_int >= 400:
        k_moek = 130  # юг
    elif h_warm_int >= 250:
        k_moek = 80  # центр
    else:
        k_moek = 40  # север/Сибирь
    m = 1.3
    psi_m = 0.5
    W_m = 10 * m * k_moek * F_paved_ha * psi_m

    return AnnualVolumes(
        rain_m3_year=round(W_d, 1),
        snowmelt_m3_year=round(W_t, 1),
        irrigation_m3_year=round(W_m, 1),
        total_m3_year=round(W_d + W_t + W_m, 1),
    )
