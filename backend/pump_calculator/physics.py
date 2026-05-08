"""Phase 21 — расширенные физические расчёты для точного подбора насосов.

Содержит:
1. **Физика воды** — плотность, кинематическая вязкость, давление насыщенных
   паров от температуры (для горячих/холодных стоков и кавитации).
2. **NPSH/кавитация** — расчёт NPSHa с учётом высоты всасывания, потерь
   и температуры жидкости. Сравнение с NPSHr насоса.
3. **Местные потери** — Σζ × v²/2g для конкретного списка фитингов
   (BOM из колен, задвижек, обратных клапанов и пр.) по таблице Идельчика.
4. **Q-H полиномиальная подгонка** — метод наименьших квадратов на 3+ точках
   паспортной кривой насоса. Решение нормальных уравнений через np.linalg.solve.
5. **Рабочая точка насос+система** — пересечение Q-H кривой насоса и
   статической H_st + динамических потерь системы.
6. **Тепловая нагрузка двигателя** — проверка допустимости числа пусков
   при выбранном методе пуска (direct/star-delta/soft-start/VFD).
7. **Поправка H для типа стоков** — по примесям SS/нефтепродукты увеличиваем
   расчётный H на 5-15% для агрессивных жидкостей.

Источники:
- Идельчик. Справочник по гидравлическим сопротивлениям, 1992.
- ISO 9906:2012 / ГОСТ 6134-2007.
- NIST IAPWS-IF97 (вода).
- Karassik. Pump Handbook (4th ed.).
- СП 32.13330.2018 §6.2 — пуски в час.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

G = 9.81
P_ATM_KPA = 101.325


def density_water_kg_m3(T_celsius: float) -> float:
    """Плотность воды кг/м³ от T (°C). Tanaka 2001, ±0.001% в 0-40°C, далее ±0.05%."""
    T = T_celsius
    # Формула Tanaka 2001 (BIPM): максимум при ~3.984°C = 999.972 кг/м³
    a1, a2, a3, a4, a5 = -3.983035, 301.797, 522528.9, 69.34881, 999.974950
    return a5 * (1 - ((T + a1) ** 2) * (T + a2) / (a3 * (T + a4)))


def kinematic_viscosity_water_m2s(T_celsius: float) -> float:
    """ν воды в м²/с от T (°C). Аппроксимация Vogel ±2% в 0-100°C.

    Табличные значения IAPWS:
    T(°C)  μ(mPa·s)  ν(m²/s)
      0    1.792    1.787e-6
     10    1.307    1.306e-6
     20    1.002    1.004e-6
     50    0.547    0.553e-6
     80    0.355    0.365e-6
    100    0.282    0.295e-6
    """
    T = T_celsius
    # Простая интерполяция по табличным данным IAPWS — точнее эмпирических формул
    # в диапазоне 0-100°C для типовых задач инженерного подбора насосов.
    table = [
        (0, 1.787e-6),
        (10, 1.306e-6),
        (20, 1.004e-6),
        (30, 0.801e-6),
        (40, 0.658e-6),
        (50, 0.553e-6),
        (60, 0.475e-6),
        (70, 0.413e-6),
        (80, 0.365e-6),
        (90, 0.326e-6),
        (100, 0.295e-6),
    ]
    if T <= table[0][0]:
        return table[0][1]
    if T >= table[-1][0]:
        return table[-1][1]
    for i in range(len(table) - 1):
        T1, nu1 = table[i]
        T2, nu2 = table[i + 1]
        if T1 <= T <= T2:
            return nu1 + (nu2 - nu1) * (T - T1) / (T2 - T1)
    return table[-1][1]


def vapor_pressure_water_kpa(T_celsius: float) -> float:
    """Давление насыщенных паров воды в кПа от T (°C). Антуан, ±0.5 кПа."""
    T = max(T_celsius, 0.01)
    A, B, C = 8.07131, 1730.63, 233.426
    p_mmhg = 10 ** (A - B / (T + C))
    return p_mmhg * 0.133322


@dataclass
class CavitationCheck:
    npsha_m: float
    npshr_m: float
    margin_m: float
    safe: bool
    warning: str | None
    vapor_pressure_kpa: float
    density_kg_m3: float


def calc_npsha_m(
    H_suction_m: float,
    T_celsius: float = 20.0,
    H_friction_suction_m: float = 0.0,
    P_atm_kpa: float = P_ATM_KPA,
) -> float:
    """Доступный NPSH (м водяного столба).

    NPSHa = (P_atm - P_vap)/(ρg) - H_suction - H_friction_suction

    H_suction:
    - **отрицательное** для затопленного насоса (погружного, dry-well с подпором)
    - **положительное** для насоса выше уровня жидкости (сухой котлован)
    """
    rho = density_water_kg_m3(T_celsius)
    p_vap = vapor_pressure_water_kpa(T_celsius)
    h_atm = (P_atm_kpa * 1000.0) / (rho * G)
    h_vap = (p_vap * 1000.0) / (rho * G)
    return h_atm - h_vap - H_suction_m - H_friction_suction_m


def check_cavitation(
    H_suction_m: float,
    npshr_m: float,
    T_celsius: float = 20.0,
    H_friction_suction_m: float = 0.0,
    P_atm_kpa: float = P_ATM_KPA,
    safety_margin_m: float = 0.5,
) -> CavitationCheck:
    npsha = calc_npsha_m(H_suction_m, T_celsius, H_friction_suction_m, P_atm_kpa)
    margin = npsha - npshr_m
    safe = margin >= safety_margin_m
    warning = None
    if not safe:
        if margin < 0:
            warning = (
                f"Кавитация: NPSHa ({npsha:.1f} м) < NPSHr ({npshr_m:.1f} м). "
                f"Дефицит {abs(margin):.1f} м."
            )
        else:
            warning = (
                f"Малый запас: NPSHa-NPSHr = {margin:.1f} м, "
                f"рекомендация ≥{safety_margin_m} м."
            )
    return CavitationCheck(
        npsha_m=round(npsha, 2),
        npshr_m=npshr_m,
        margin_m=round(margin, 2),
        safe=safe,
        warning=warning,
        vapor_pressure_kpa=round(vapor_pressure_water_kpa(T_celsius), 3),
        density_kg_m3=round(density_water_kg_m3(T_celsius), 1),
    )


# ζ-коэффициенты по Идельчику (1992) и BS EN 806-3
ZETA_TABLE = {
    "entrance_sharp": 0.5,
    "entrance_rounded": 0.25,
    "entrance_protruding": 1.0,
    "exit_to_reservoir": 1.0,
    "elbow_45": 0.3,
    "elbow_90": 0.3,
    "elbow_90_sharp": 1.0,
    "elbow_180_uturn": 1.5,
    "tee_through": 0.4,
    "tee_branch": 1.0,
    "gate_valve_open": 0.15,
    "gate_valve_75pct": 1.0,
    "gate_valve_50pct": 4.5,
    "ball_valve_open": 0.05,
    "butterfly_valve_open": 0.5,
    "check_valve_swing": 1.5,
    "check_valve_lift": 4.5,
    "check_valve_disk_silent": 2.0,
    "strainer_basket": 1.2,
    "strainer_y_type": 0.5,
    "diffuser_2_to_1": 0.3,
    "reducer_1_to_2": 0.05,
    "flowmeter_electromagnetic": 0.5,
    "flowmeter_ultrasonic": 0.2,
    "pressure_gauge_tap": 0.05,
}


@dataclass
class FittingsBOM:
    entrance_sharp: int = 0
    entrance_rounded: int = 0
    entrance_protruding: int = 0
    exit_to_reservoir: int = 0
    elbows_45: int = 0
    elbows_90: int = 0
    elbows_90_sharp: int = 0
    elbows_180: int = 0
    tees_through: int = 0
    tees_branch: int = 0
    gate_valves: int = 0
    gate_valves_50pct: int = 0
    ball_valves: int = 0
    butterfly_valves: int = 0
    check_valves_swing: int = 0
    check_valves_lift: int = 0
    check_valves_disk_silent: int = 0
    strainers_basket: int = 0
    strainers_y: int = 0
    flowmeters_em: int = 0
    flowmeters_us: int = 0
    custom_zeta: list[float] = field(default_factory=list)

    def total_zeta(self) -> float:
        z = 0.0
        z += self.entrance_sharp * ZETA_TABLE["entrance_sharp"]
        z += self.entrance_rounded * ZETA_TABLE["entrance_rounded"]
        z += self.entrance_protruding * ZETA_TABLE["entrance_protruding"]
        z += self.exit_to_reservoir * ZETA_TABLE["exit_to_reservoir"]
        z += self.elbows_45 * ZETA_TABLE["elbow_45"]
        z += self.elbows_90 * ZETA_TABLE["elbow_90"]
        z += self.elbows_90_sharp * ZETA_TABLE["elbow_90_sharp"]
        z += self.elbows_180 * ZETA_TABLE["elbow_180_uturn"]
        z += self.tees_through * ZETA_TABLE["tee_through"]
        z += self.tees_branch * ZETA_TABLE["tee_branch"]
        z += self.gate_valves * ZETA_TABLE["gate_valve_open"]
        z += self.gate_valves_50pct * ZETA_TABLE["gate_valve_50pct"]
        z += self.ball_valves * ZETA_TABLE["ball_valve_open"]
        z += self.butterfly_valves * ZETA_TABLE["butterfly_valve_open"]
        z += self.check_valves_swing * ZETA_TABLE["check_valve_swing"]
        z += self.check_valves_lift * ZETA_TABLE["check_valve_lift"]
        z += self.check_valves_disk_silent * ZETA_TABLE["check_valve_disk_silent"]
        z += self.strainers_basket * ZETA_TABLE["strainer_basket"]
        z += self.strainers_y * ZETA_TABLE["strainer_y_type"]
        z += self.flowmeters_em * ZETA_TABLE["flowmeter_electromagnetic"]
        z += self.flowmeters_us * ZETA_TABLE["flowmeter_ultrasonic"]
        z += sum(self.custom_zeta)
        return z


def calc_local_losses_h_m(bom: FittingsBOM, v_ms: float) -> tuple[float, float]:
    """H_местн = Σζ × v²/(2g). Возвращает (Σζ, H_м)."""
    sum_z = bom.total_zeta()
    h_m = sum_z * v_ms**2 / (2 * G)
    return round(sum_z, 3), round(h_m, 3)


def fit_qh_polynomial(points: list[tuple[float, float]], degree: int = 2) -> list[float]:
    """Q-H подгонка по МНК. Возвращает коэффициенты [a0, a1, a2, ...]."""
    if len(points) < degree + 1:
        raise ValueError(
            f"Для полинома {degree}-й степени нужно >= {degree+1} точек, "
            f"передано {len(points)}."
        )
    Q_arr = np.array([p[0] for p in points])
    H_arr = np.array([p[1] for p in points])
    coeffs_high_to_low = np.polyfit(Q_arr, H_arr, degree)
    return list(reversed(coeffs_high_to_low.tolist()))


def evaluate_qh_polynomial(coeffs: list[float], Q: float) -> float:
    """H(Q) = Σ coeffs[i] × Q^i."""
    return sum(c * Q**i for i, c in enumerate(coeffs))


def find_operating_point(
    pump_coeffs: list[float],
    system_static_h_m: float,
    system_friction_factor_per_q2: float,
    Q_min: float = 0.01,
    Q_max: float = 1e4,
    tolerance: float = 0.001,
    max_iter: int = 100,
) -> tuple[float, float]:
    """Точка пересечения Q-H насоса и характеристики системы.

    Q-H системы: H_sys(Q) = H_st + k_f · Q²
    Биссекция: f(Q) = H_pump(Q) - H_sys(Q) = 0.
    """
    def diff(Q):
        return evaluate_qh_polynomial(pump_coeffs, Q) - (
            system_static_h_m + system_friction_factor_per_q2 * Q**2
        )

    a, b = Q_min, Q_max
    fa, fb = diff(a), diff(b)
    if fa * fb > 0:
        target_Q = Q_max if fa > 0 else Q_min
        return target_Q, evaluate_qh_polynomial(pump_coeffs, target_Q)

    for _ in range(max_iter):
        mid = (a + b) / 2
        fm = diff(mid)
        if abs(fm) < tolerance:
            break
        if fa * fm < 0:
            b, fb = mid, fm
        else:
            a, fa = mid, fm

    Q_op = (a + b) / 2
    H_op = evaluate_qh_polynomial(pump_coeffs, Q_op)
    return round(Q_op, 3), round(H_op, 3)


# Кратность пускового тока и тепловыделение по IEC 60034-1
STARTING_METHODS = {
    "direct": {
        "I_start_to_I_nom": 7.0,
        "thermal_load_factor": 1.0,
        "max_starts_per_hour_curve": (
            (0.5, 30), (1.5, 25), (3, 20), (7.5, 15), (15, 12),
            (30, 10), (55, 8), (90, 6), (200, 4), (1000, 2),
        ),
    },
    "star_delta": {
        "I_start_to_I_nom": 2.5,
        "thermal_load_factor": 0.45,
        "max_starts_per_hour_curve": (
            (0.5, 60), (1.5, 50), (3, 40), (7.5, 30), (15, 25),
            (30, 20), (55, 15), (90, 12), (200, 8), (1000, 4),
        ),
    },
    "soft_start": {
        "I_start_to_I_nom": 2.5,
        "thermal_load_factor": 0.40,
        "max_starts_per_hour_curve": (
            (0.5, 60), (1.5, 50), (3, 45), (7.5, 35), (15, 30),
            (30, 25), (55, 20), (90, 15), (200, 10), (1000, 5),
        ),
    },
    "VFD": {
        "I_start_to_I_nom": 1.2,
        "thermal_load_factor": 0.05,
        "max_starts_per_hour_curve": (
            (0.5, 120), (1.5, 100), (3, 80), (7.5, 60), (15, 50),
            (30, 40), (55, 30), (90, 25), (200, 20), (1000, 15),
        ),
    },
}


def calc_motor_starting_current(P_motor_kw: float, starting_method: str) -> float:
    method = STARTING_METHODS.get(starting_method, STARTING_METHODS["direct"])
    return method["I_start_to_I_nom"]


def thermal_load_check(
    starts_per_hour: int,
    P_motor_kw: float,
    starting_method: str,
) -> dict:
    """Проверка пусков по IEC 60034-1."""
    method = STARTING_METHODS.get(starting_method)
    if method is None:
        return {
            "ok": False,
            "max_allowed_per_hour": 0,
            "recommendation": f"Неизвестный метод пуска: {starting_method}",
        }

    curve = method["max_starts_per_hour_curve"]
    max_allowed = curve[-1][1]
    for (p_lim, n_lim) in curve:
        if P_motor_kw <= p_lim:
            max_allowed = n_lim
            break

    ok = starts_per_hour <= max_allowed
    rec = None
    if not ok:
        better_methods = []
        for m_name, m_data in STARTING_METHODS.items():
            for (p_lim, n_lim) in m_data["max_starts_per_hour_curve"]:
                if P_motor_kw <= p_lim and n_lim >= starts_per_hour:
                    better_methods.append(m_name)
                    break
        rec = (
            f"Метод '{starting_method}' допускает {max_allowed} пусков/час. "
            f"Запрошено {starts_per_hour}. "
        )
        if better_methods:
            rec += f"Используйте: {', '.join(set(better_methods))}."
        else:
            rec += "Снизьте число пусков (увеличьте sump) или примените VFD."

    return {
        "ok": ok,
        "max_allowed_per_hour": max_allowed,
        "starts_requested_per_hour": starts_per_hour,
        "starting_method": starting_method,
        "thermal_load_factor": method["thermal_load_factor"],
        "I_start_to_I_nom": method["I_start_to_I_nom"],
        "recommendation": rec,
    }


def adjust_h_for_wastewater(
    H_clean_m: float,
    suspended_solids_mg_l: float = 0,
    oil_products_mg_l: float = 0,
    fiber_content_pct: float = 0,
) -> tuple[float, str]:
    """Поправка H для агрессивных стоков (фильтрат ТКО, нефтепродукты, волокна)."""
    factor = 1.0
    reasons = []
    if suspended_solids_mg_l >= 5000:
        factor *= 1.10
        reasons.append(f"взвешенные {suspended_solids_mg_l:.0f} мг/л (+10%)")
    elif suspended_solids_mg_l >= 1000:
        factor *= 1.05
        reasons.append(f"взвешенные {suspended_solids_mg_l:.0f} мг/л (+5%)")
    if oil_products_mg_l >= 1000:
        factor *= 1.06
        reasons.append(f"нефтепродукты {oil_products_mg_l:.0f} мг/л (+6%)")
    elif oil_products_mg_l >= 100:
        factor *= 1.03
        reasons.append(f"нефтепродукты {oil_products_mg_l:.0f} мг/л (+3%)")
    if fiber_content_pct >= 1:
        factor *= 1.05
        reasons.append(f"волокна {fiber_content_pct:.1f}% (+5%)")
    H_corr = round(H_clean_m * factor, 3)
    if not reasons:
        reasons_text = "чистая среда (поправка 0%)"
    else:
        reasons_text = "; ".join(reasons) + f"; итого ×{factor:.3f}"
    return H_corr, reasons_text
