"""Гидравлические расчёты: Дарси-Альтшуль, Σζ Идельчика, Жуковский, AOR/POR.

Использует CalebBell/fluids (MIT) для friction_factor.
Соответствует formulas.md v0.2 и dependencies_map.md v0.2.
"""

from __future__ import annotations

import math

import fluids

from pump_calculator import catalog
from pump_calculator.schemas import ComputedHydraulics, L0Input, L1Input

G = 9.81  # м/с²
NU_WATER_20C = 1.01e-6  # м²/с


def round_up_to_standard(value_mm: float, ladder: list[float]) -> float:
    """Округление вверх до ближайшего из стандартного ряда."""
    for d in ladder:
        if d >= value_mm:
            return d
    return ladder[-1]  # всё что больше — берём максимальный


def auto_select_diameter_mm(Q_m3h: float, v_target_ms: float = 1.2) -> float:
    """Шаг 1 алгоритма: подбор D напорного по целевой скорости.

    Default v_target = 1.2 м/с (СП 32, диапазон 1.0–1.5).
    """
    Q_si = Q_m3h / 3600.0  # м³/с
    D_calc = math.sqrt(4 * Q_si / (math.pi * v_target_ms))  # м
    D_mm_calc = D_calc * 1000.0
    return round_up_to_standard(D_mm_calc, catalog.get_standard_diameters_mm())


def calc_velocity_ms(Q_m3h: float, D_mm: float) -> float:
    """v = 4Q / (π·D²)."""
    Q_si = Q_m3h / 3600.0
    D_si = D_mm / 1000.0
    return 4 * Q_si / (math.pi * D_si**2)


def calc_friction_factor(Re: float, eD: float) -> float:
    """λ через CalebBell/fluids.friction_factor (Colebrook-White).

    Для Re < 2300 — ламинар (64/Re).
    Для Re ≥ 4000 — Colebrook через fluids (универсально).
    Между ними — линейная интерполяция (хотя это редкий случай для напорной канализации).
    """
    if Re < 2300:
        return 64.0 / Re
    if Re >= 4000:
        return fluids.friction_factor(Re=Re, eD=eD)
    # переходная зона — линейная интерполяция
    f_lam = 64.0 / 2300
    f_turb = fluids.friction_factor(Re=4000, eD=eD)
    return f_lam + (f_turb - f_lam) * (Re - 2300) / (4000 - 2300)


def compute_hydraulics(L0: L0Input, L1: L1Input | None = None) -> ComputedHydraulics:
    """Шаги 1-2 алгоритма: D + H_full.

    H_full = (dH + H_тр + H_м) × (1 + safety)
    H_тр через Дарси-Альтшуль (fluids).
    H_м через Σζ × v² / 2g (Идельчик, типовая обвязка КНС).
    """
    # Параметры из L1 или дефолты
    pipe_material = (L1.pipe_material if L1 and L1.pipe_material else "pe100_sdr17")
    k_e_mm = catalog.get_default_pipe_roughness_mm(pipe_material)

    # 1. Диаметр
    D_mm = (L1.pipe_D_mm if L1 and L1.pipe_D_mm else auto_select_diameter_mm(L0.Q_m3h))
    D_si = D_mm / 1000.0

    # 2. Скорость и Re
    v_ms = calc_velocity_ms(L0.Q_m3h, D_mm)
    Re = v_ms * D_si / NU_WATER_20C
    eD = (k_e_mm / 1000.0) / D_si

    # 3. λ и H_тр
    fd = calc_friction_factor(Re, eD)
    H_tr = fd * (L0.L_m / D_si) * (v_ms**2) / (2 * G) if L0.L_m > 0 else 0.0

    # 4. Σζ для типовой обвязки + H_м
    sum_zeta = catalog.get_typical_obvyazka_sum_zeta()
    H_m = sum_zeta * (v_ms**2) / (2 * G)

    # 5. Запас
    safety = 0.05 if L0.L_m == 0 else (0.15 if L0.L_m > 1000 else 0.10)
    H_full = (L0.dH_m + H_tr + H_m) * (1 + safety)

    return ComputedHydraulics(
        D_mm=D_mm,
        v_ms=round(v_ms, 4),
        Re=round(Re, 1),
        friction_factor=round(fd, 6),
        H_tr_m=round(H_tr, 3),
        sum_zeta=sum_zeta,
        H_m_m=round(H_m, 3),
        H_full_m=round(H_full, 3),
        safety_factor=safety,
    )


def aor_zone(Q_m3h: float, Q_BEP_m3h: float | None) -> str | None:
    """Возвращает 'POR' / 'AOR' / 'outside' / None (если Q_BEP неизвестен)."""
    if not Q_BEP_m3h:
        return None
    ratio = Q_m3h / Q_BEP_m3h
    limits = catalog.get_aor_por_limits()
    por_min, por_max = limits["POR"]
    aor_min, aor_max = limits["AOR"]
    if por_min <= ratio <= por_max:
        return "POR"
    if aor_min <= ratio <= aor_max:
        return "AOR"
    return "outside"


def zhukovsky_shock_m(v_ms: float, pipe_material: str = "pe100_sdr17") -> float:
    """Гидроудар по Жуковскому: ΔH = a·v/g."""
    coeffs = catalog.load_coefficients()
    wave_table = coeffs["wave_speed_ms_by_pipe_material"]["values"]
    # Маппим имена материалов → ключи таблицы скорости звука
    a_key_map = {
        "pe100_sdr17": "pe100",
        "korsis_pe_corrugated": "korsis_pe",
        "steel_seamless_new": "steel",
        "steel_welded_new": "steel",
        "cast_iron_new": "cast_iron",
        "pvc": "pvc",
        "pp": "pp",
        "concrete": "concrete",
    }
    key = a_key_map.get(pipe_material, "pe100")
    a_ms = wave_table[key]["default"]
    return round(a_ms * v_ms / G, 2)
