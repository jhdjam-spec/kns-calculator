"""Гидравлические расчёты: Дарси-Альтшуль, Σζ Идельчика, Жуковский, AOR/POR.

Friction factor по явной аппроксимации Swamee-Jain (1976) — без итераций
Colebrook-White, точность ~1% в диапазоне 5e3 ≤ Re ≤ 1e8 и 1e-6 ≤ eD ≤ 1e-2.
Соответствует formulas.md v0.2 и dependencies_map.md v0.2.
"""

from __future__ import annotations

import math

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


def auto_select_diameter_mm(
    Q_m3h: float,
    v_target_ms: float = 1.2,
    v_min_ms: float = 1.0,
) -> float:
    """Шаг 1 алгоритма: подбор D напорного по целевой скорости.

    Default v_target = 1.2 м/с (СП 32, диапазон 1.0–1.5).

    §15.9 — фильтр v_min: после round_up_to_standard выбранный D может
    давать v < v_min (если шаг лестницы крупный). Тогда выбираем
    **наибольший D**, при котором v ≥ v_min — это защита от заиливания
    напорной канализации (СП 32 §5.4: для бытовых стоков 1.0 м/с —
    жёсткий минимум).
    """
    Q_si = Q_m3h / 3600.0  # м³/с
    D_calc = math.sqrt(4 * Q_si / (math.pi * v_target_ms))  # м
    D_mm_calc = D_calc * 1000.0
    ladder = catalog.get_standard_diameters_mm()
    D_initial = round_up_to_standard(D_mm_calc, ladder)

    # §15.9 — проверка v_min на выбранном D
    v_at_D = calc_velocity_ms(Q_m3h, D_initial)
    if v_at_D >= v_min_ms:
        return D_initial

    # v < v_min → надо уменьшать D, пока скорость не вырастет до v_min.
    # Идём по лестнице вниз от D_initial.
    for d in reversed(ladder):
        if d > D_initial:
            continue
        if calc_velocity_ms(Q_m3h, d) >= v_min_ms:
            return d
    # Если даже минимальный D не даёт v_min — возвращаем минимальный
    # (Q настолько мал, что любой стандарт даст v < 1 м/с — это сигнал
    # пересмотреть L0 / выбрать pulsed mode).
    return ladder[0]


def calc_velocity_ms(Q_m3h: float, D_mm: float) -> float:
    """v = 4Q / (π·D²)."""
    Q_si = Q_m3h / 3600.0
    D_si = D_mm / 1000.0
    return 4 * Q_si / (math.pi * D_si**2)


def _swamee_jain(Re: float, eD: float) -> float:
    # f = 0.25 / (log10(eD/3.7 + 5.74/Re^0.9))²
    arg = eD / 3.7 + 5.74 / (Re**0.9)
    return 0.25 / (math.log10(arg) ** 2)


def calc_friction_factor(Re: float, eD: float) -> float:
    """λ для напорного трубопровода.

    Re < 2300 — ламинар (64/Re).
    Re ≥ 4000 — Swamee-Jain (1976), явная аппроксимация Colebrook-White
    с погрешностью ≤1% в диапазоне 5·10³ ≤ Re ≤ 10⁸ и 10⁻⁶ ≤ eD ≤ 10⁻².
    Переход 2300–4000 — линейная интерполяция.
    """
    if Re < 2300:
        return 64.0 / Re
    if Re >= 4000:
        return _swamee_jain(Re, eD)
    f_lam = 64.0 / 2300
    f_turb = _swamee_jain(4000, eD)
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
