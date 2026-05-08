"""БД коэффициентов поверхностей по СП 32.13330.2018 прил. Б (бывшие табл. Ж.6 / Ж.7).

ψ_д — средневзвешенный коэффициент стока для дождевых вод
ψ_T — коэффициент стока для талых
Z   — коэффициент покрова для метода предельных интенсивностей (формула Q_r)
"""
from __future__ import annotations

# Z коэффициенты покрова (СП 32.13330.2018 табл. Б.2)
# psi_d — для упрощённых расчётов (годовой объём)
# psi_t — для талого стока
# Все значения соответствуют q20=100 л/с·га; пересчитываются при других q20
SURFACE_COEFFS: dict[str, dict[str, float]] = {
    "asphalt": {"Z": 0.33, "psi_d": 0.95, "psi_t": 0.95},
    "concrete": {"Z": 0.32, "psi_d": 0.92, "psi_t": 0.90},
    "roof": {"Z": 0.33, "psi_d": 0.95, "psi_t": 0.95},  # обобщённая кровля
    "paving_dense": {"Z": 0.224, "psi_d": 0.60, "psi_t": 0.60},
    "paving_loose": {"Z": 0.145, "psi_d": 0.45, "psi_t": 0.50},
    "gravel": {"Z": 0.10, "psi_d": 0.30, "psi_t": 0.40},
    "crushed_stone": {"Z": 0.125, "psi_d": 0.42, "psi_t": 0.50},
    "soil": {"Z": 0.064, "psi_d": 0.20, "psi_t": 0.30},
    "lawn": {"Z": 0.038, "psi_d": 0.10, "psi_t": 0.20},
    "forest": {"Z": 0.025, "psi_d": 0.08, "psi_t": 0.15},
    "water": {"Z": 1.0, "psi_d": 1.0, "psi_t": 1.0},
}


def calc_z_mid(surfaces_dict: dict[str, float]) -> tuple[float, float]:
    """Рассчитать средневзвешенный Z_mid и общую площадь.

    Args:
        surfaces_dict: ключ — id поверхности, значение — площадь в га

    Returns:
        (Z_mid, F_total_ha)
    """
    F_total = sum(surfaces_dict.values())
    if F_total == 0:
        return 0.0, 0.0
    z_sum = 0.0
    for surf_id, area in surfaces_dict.items():
        coeffs = SURFACE_COEFFS.get(surf_id)
        if not coeffs:
            continue
        z_sum += coeffs["Z"] * area
    return z_sum / F_total, F_total


def calc_psi_d_mid(surfaces_dict: dict[str, float]) -> tuple[float, float]:
    """Средневзвешенный ψ_д для расчёта годового объёма дождевых."""
    F_total = sum(surfaces_dict.values())
    if F_total == 0:
        return 0.0, 0.0
    psi_sum = 0.0
    for surf_id, area in surfaces_dict.items():
        coeffs = SURFACE_COEFFS.get(surf_id)
        if not coeffs:
            continue
        psi_sum += coeffs["psi_d"] * area
    return psi_sum / F_total, F_total


def calc_psi_design(surfaces_dict: dict[str, float]) -> tuple[float, float]:
    """ψ_mid для расчёта суточного объёма (СП 32 п. 7.5).

    Используются значения для асфальт/кровли = 0.95, для газонов = 0.10.
    Это стандартные ψ для проектирования ЛОС.
    """
    return calc_psi_d_mid(surfaces_dict)


def surfaces_from_breakdown(breakdown) -> dict[str, float]:
    """Конвертировать SurfaceBreakdown в dict для расчётов."""
    return {
        "roof": breakdown.roof_ha,
        "asphalt": breakdown.asphalt_ha,
        "paving_dense": breakdown.paving_dense_ha,
        "paving_loose": breakdown.paving_loose_ha,
        "gravel": breakdown.gravel_ha,
        "crushed_stone": breakdown.crushed_stone_ha,
        "soil": breakdown.soil_ha,
        "lawn": breakdown.lawn_ha,
        "forest": breakdown.forest_ha,
        "water": breakdown.water_ha,
    }
