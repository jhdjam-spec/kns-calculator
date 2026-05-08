"""Подбор сечения кабеля по ПУЭ 1.3 + по падению напряжения.

Алгоритм:
1. По нагреву (длительный допустимый ток) — ПУЭ табл. 1.3.4-1.3.7
2. По падению напряжения ΔU ≤ 5% (для двигателя) — формула
3. По термической стойкости при КЗ (опционально)
4. Берём максимальное из (1, 2, 3) сечение

Формула ΔU для трёхфазного:
    ΔU% = √3·I·L·(R·cosφ + X·sinφ) / U_ном × 100

Где R, X — погонные сопротивления кабеля (Ом/км), L — длина в км.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class CableSelection:
    section_mm2: float
    cable_type: str          # ВВГ, КГ, АВВГ
    n_cores: int             # число жил
    delta_u_percent: float
    selection_criterion: str  # "по нагреву" | "по падению напр." | "по КЗ"
    notes: list[str]


# Стандартная сетка сечений (мм²)
CABLE_SECTIONS_MM2 = [
    1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400, 500, 630
]

# Длительно допустимый ток для меди в воздухе (ПУЭ табл. 1.3.4 — упрощённо)
# Кабель 4-жильный (3Ф+N), способ прокладки — в воздухе.
# Реально таблица сложнее (есть поправки на t°C, число цепей).
COPPER_CURRENT_AIR_A: dict[float, int] = {
    1.5: 19, 2.5: 27, 4: 38, 6: 50, 10: 70, 16: 90, 25: 115, 35: 140,
    50: 175, 70: 215, 95: 260, 120: 300, 150: 350, 185: 405, 240: 480,
    300: 550, 400: 645, 500: 750, 630: 870,
}

# Удельное активное сопротивление для меди при 20°C (Ом/км)
COPPER_R_OHM_KM: dict[float, float] = {
    1.5: 12.1, 2.5: 7.41, 4: 4.61, 6: 3.08, 10: 1.83, 16: 1.15, 25: 0.727,
    35: 0.524, 50: 0.387, 70: 0.268, 95: 0.193, 120: 0.153, 150: 0.124,
    185: 0.0991, 240: 0.0754, 300: 0.0601, 400: 0.0470, 500: 0.0366, 630: 0.0283,
}

# Удельное реактивное сопротивление (приблизительно, для одножильного кабеля)
COPPER_X_OHM_KM = 0.08


def select_cable_section(
    I_load_a: float,
    L_m: float,
    U_v: int = 400,
    cos_phi: float = 0.85,
    max_delta_u_pct: float = 5.0,
    correction_factor_temp: float = 1.0,
    correction_factor_grouping: float = 1.0,
) -> CableSelection:
    """Подбор сечения кабеля по двум критериям.

    Args:
        I_load_a: расчётный ток нагрузки, А (с учётом коэф. использования)
        L_m: длина кабельной линии, м
        U_v: номинальное напряжение, В (380/400 для 3Ф)
        cos_phi: коэф. мощности
        max_delta_u_pct: допустимое падение, % (5% для двигателей по ГОСТ)
        correction_factor_temp: поправка на температуру среды (0.8-1.0)
        correction_factor_grouping: поправка на число параллельных кабелей
    """
    notes: list[str] = []

    # 1. По нагреву: ищем минимальное сечение, у которого I_доп ≥ I_load
    I_required = I_load_a / (correction_factor_temp * correction_factor_grouping)
    section_by_heat = None
    for s in CABLE_SECTIONS_MM2:
        if COPPER_CURRENT_AIR_A[s] >= I_required:
            section_by_heat = s
            break
    if section_by_heat is None:
        section_by_heat = CABLE_SECTIONS_MM2[-1]
        notes.append("Нагрузка превышает 870 А — нужны параллельные кабели или шины")

    notes.append(
        f"По нагреву (с учётом поправок K_t={correction_factor_temp}, K_n={correction_factor_grouping}): "
        f"I_требуемое = {I_required:.1f} А → S ≥ {section_by_heat} мм²"
    )

    # 2. По падению напряжения: ΔU% = √3·I·L·(R·cosφ+X·sinφ)·100 / U
    # Перебираем сечения от section_by_heat и больше, пока ΔU не попадёт в норму.
    sin_phi = math.sin(math.acos(cos_phi))
    L_km = L_m / 1000.0

    section_final = section_by_heat
    delta_u_pct = 0.0
    for s in CABLE_SECTIONS_MM2:
        if s < section_by_heat:
            continue
        R = COPPER_R_OHM_KM[s]
        X = COPPER_X_OHM_KM
        if U_v >= 380:
            delta_u = math.sqrt(3) * I_load_a * L_km * (R * cos_phi + X * sin_phi)
        else:
            delta_u = 2 * I_load_a * L_km * (R * cos_phi + X * sin_phi)
        delta_u_pct = (delta_u / U_v) * 100.0
        if delta_u_pct <= max_delta_u_pct:
            section_final = s
            break
    else:
        section_final = CABLE_SECTIONS_MM2[-1]

    if section_final > section_by_heat:
        notes.append(
            f"По ΔU: при S={section_by_heat} ΔU={delta_u_pct:.2f}%>{max_delta_u_pct}%, "
            f"увеличено до S={section_final} мм²"
        )
        criterion = "по падению напряжения"
    else:
        notes.append(f"ΔU при S={section_final}: {delta_u_pct:.2f}% ≤ {max_delta_u_pct}%")
        criterion = "по нагреву"

    cable_type = "ВВГнг(А)-LS"  # типовой выбор
    n_cores = 5 if U_v >= 380 else 3  # 3+N+PE для 3Ф, L+N+PE для 1Ф

    return CableSelection(
        section_mm2=section_final,
        cable_type=cable_type,
        n_cores=n_cores,
        delta_u_percent=round(delta_u_pct, 2),
        selection_criterion=criterion,
        notes=notes,
    )
