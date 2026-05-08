"""БД коэффициентов поверхностей по СП 32.13330 (две редакции: 2012 и 2018).

ψ_д — средневзвешенный коэффициент стока для дождевых вод
ψ_T — коэффициент стока для талых
Z   — коэффициент покрова для метода предельных интенсивностей (формула Q_r)

Редакции отличаются в первую очередь значениями Z для асфальта/кровли:
- СП 32.13330.2012 (табл. 14)  — Z_асфальт ≈ 0.28, более консервативные.
- СП 32.13330.2018 (прил. Б.2) — Z_асфальт ≈ 0.33, обновлены по мониторингу.

Эталонные расчёты ВБД Екатеринбург / Уташ ИБИОКС / Белогорский выполнены по
СП 32.13330.2012. Поэтому редакция передаётся явно через `sp_revision` в
StormInput — без дефолта, чтобы пользователь сделал осознанный выбор.
"""
from __future__ import annotations

from typing import Literal

SpRevision = Literal["SP_32_2012", "SP_32_2018"]


# СП 32.13330.2012 табл. 14 (для метода предельных интенсивностей)
# Источник: эталоны ВБД Екатеринбург (К2 = 540 л/с при F=7.7 га, асфальт+газон)
SURFACE_COEFFS_2012: dict[str, dict[str, float]] = {
    "asphalt": {"Z": 0.28, "psi_d": 0.95, "psi_t": 0.95},
    "concrete": {"Z": 0.27, "psi_d": 0.90, "psi_t": 0.90},
    "roof": {"Z": 0.28, "psi_d": 0.95, "psi_t": 0.95},
    "paving_dense": {"Z": 0.20, "psi_d": 0.60, "psi_t": 0.60},
    "paving_loose": {"Z": 0.125, "psi_d": 0.45, "psi_t": 0.50},
    "gravel": {"Z": 0.09, "psi_d": 0.30, "psi_t": 0.40},
    "crushed_stone": {"Z": 0.11, "psi_d": 0.42, "psi_t": 0.50},
    "soil": {"Z": 0.06, "psi_d": 0.20, "psi_t": 0.30},
    "lawn": {"Z": 0.038, "psi_d": 0.10, "psi_t": 0.20},
    "forest": {"Z": 0.025, "psi_d": 0.08, "psi_t": 0.15},
    "water": {"Z": 1.0, "psi_d": 1.0, "psi_t": 1.0},
}

# СП 32.13330.2018 прил. Б.2 (обновлённая редакция)
SURFACE_COEFFS_2018: dict[str, dict[str, float]] = {
    "asphalt": {"Z": 0.33, "psi_d": 0.95, "psi_t": 0.95},
    "concrete": {"Z": 0.32, "psi_d": 0.92, "psi_t": 0.90},
    "roof": {"Z": 0.33, "psi_d": 0.95, "psi_t": 0.95},
    "paving_dense": {"Z": 0.224, "psi_d": 0.60, "psi_t": 0.60},
    "paving_loose": {"Z": 0.145, "psi_d": 0.45, "psi_t": 0.50},
    "gravel": {"Z": 0.10, "psi_d": 0.30, "psi_t": 0.40},
    "crushed_stone": {"Z": 0.125, "psi_d": 0.42, "psi_t": 0.50},
    "soil": {"Z": 0.064, "psi_d": 0.20, "psi_t": 0.30},
    "lawn": {"Z": 0.038, "psi_d": 0.10, "psi_t": 0.20},
    "forest": {"Z": 0.025, "psi_d": 0.08, "psi_t": 0.15},
    "water": {"Z": 1.0, "psi_d": 1.0, "psi_t": 1.0},
}


def get_coeffs_table(sp_revision: SpRevision) -> dict[str, dict[str, float]]:
    """Получить таблицу коэффициентов для указанной редакции СП 32."""
    if sp_revision == "SP_32_2012":
        return SURFACE_COEFFS_2012
    if sp_revision == "SP_32_2018":
        return SURFACE_COEFFS_2018
    raise ValueError(
        f"Unknown sp_revision='{sp_revision}'. Use 'SP_32_2012' or 'SP_32_2018'"
    )


def calc_z_mid(
    surfaces_dict: dict[str, float],
    sp_revision: SpRevision,
) -> tuple[float, float]:
    """Рассчитать средневзвешенный Z_mid и общую площадь.

    Args:
        surfaces_dict: ключ — id поверхности, значение — площадь в га
        sp_revision: 'SP_32_2012' или 'SP_32_2018'

    Returns:
        (Z_mid, F_total_ha)
    """
    table = get_coeffs_table(sp_revision)
    F_total = sum(surfaces_dict.values())
    if F_total == 0:
        return 0.0, 0.0
    z_sum = 0.0
    for surf_id, area in surfaces_dict.items():
        coeffs = table.get(surf_id)
        if not coeffs:
            continue
        z_sum += coeffs["Z"] * area
    return z_sum / F_total, F_total


def calc_psi_d_mid(
    surfaces_dict: dict[str, float],
    sp_revision: SpRevision,
) -> tuple[float, float]:
    """Средневзвешенный ψ_д для расчёта годового объёма дождевых."""
    table = get_coeffs_table(sp_revision)
    F_total = sum(surfaces_dict.values())
    if F_total == 0:
        return 0.0, 0.0
    psi_sum = 0.0
    for surf_id, area in surfaces_dict.items():
        coeffs = table.get(surf_id)
        if not coeffs:
            continue
        psi_sum += coeffs["psi_d"] * area
    return psi_sum / F_total, F_total


def calc_psi_design(
    surfaces_dict: dict[str, float],
    sp_revision: SpRevision,
) -> tuple[float, float]:
    """ψ_mid для расчёта суточного объёма (СП 32 п. 7.5)."""
    return calc_psi_d_mid(surfaces_dict, sp_revision)


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
