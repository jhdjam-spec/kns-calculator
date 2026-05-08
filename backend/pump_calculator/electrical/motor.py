"""Расчёт мощности двигателя и токов по ГОСТ IEC 60034-1.

Гидравлическая мощность насоса:
    P_hyd = ρ·g·Q·H / 1000  [Вт] = ρ·g·Q·H / 1_000_000  [кВт]
    с Q в м³/с, H в м.

Мощность на валу (с учётом КПД насоса):
    P_shaft = P_hyd / η_pump

Мощность электродвигателя (с запасом на пуск и КПД двигателя):
    P_motor = P_shaft / η_motor × K_safety

K_safety обычно 1.05-1.15 для S1 режима, 1.15-1.30 для S3 КНС.

Полный ток нагрузки:
    I_load = P_motor·1000 / (√3 · U · cos_phi · η_motor)
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class MotorPowerCalc:
    P_hydraulic_kw: float
    P_shaft_kw: float
    P_motor_required_kw: float
    P_motor_nominal_kw: float    # Округлено до стандартной сетки
    pump_efficiency: float
    motor_efficiency: float
    safety_factor: float
    nominal_current_a: float     # При U_nom, cos_phi
    starting_current_a: float    # I_пуск × I_ном
    starting_method: str
    notes: list[str]


# Стандартная сетка мощностей электродвигателей (IEC), кВт
STANDARD_MOTOR_POWERS_KW = [
    0.18, 0.25, 0.37, 0.55, 0.75, 1.1, 1.5, 2.2, 3.0, 4.0,
    5.5, 7.5, 11, 15, 18.5, 22, 30, 37, 45, 55, 75, 90, 110,
    132, 160, 200, 250, 315, 355, 400, 450, 500, 560, 630,
    710, 800, 900, 1000,
]

# Типовые КПД двигателей по классам IE (IEC 60034-30-1)
MOTOR_EFFICIENCY_BY_CLASS = {
    "IE2": 0.85,    # Standard (старый)
    "IE3": 0.90,    # Premium (стандарт после 2017)
    "IE4": 0.93,    # Super premium
    "IE5": 0.95,    # Ultra premium (для VFD)
}


def round_up_to_standard(P_kw: float) -> float:
    """Округление вверх до стандартной мощности."""
    for p_std in STANDARD_MOTOR_POWERS_KW:
        if p_std >= P_kw:
            return p_std
    return STANDARD_MOTOR_POWERS_KW[-1]


def calc_motor_power_required(
    Q_m3h: float,
    H_m: float,
    pump_efficiency: float = 0.65,
    motor_class: str = "IE3",
    safety_factor: float = 1.15,
    rho_kg_m3: float = 1000.0,
    cos_phi: float = 0.85,
    U_v: int = 400,
    starting_method: str = "soft_start",
) -> MotorPowerCalc:
    """Полный расчёт электродвигателя для насосной установки.

    Args:
        Q_m3h: подача насоса, м³/ч
        H_m: напор, м
        pump_efficiency: КПД насоса (паспортный) при BEP, 0.5-0.85
        motor_class: IE2/IE3/IE4 — класс КПД двигателя
        safety_factor: запас на пуск и колебания нагрузки
        rho_kg_m3: плотность жидкости (для стоков 1000-1100)
        cos_phi: коэффициент мощности
        U_v: номинальное напряжение, В (400 для 3Ф, 230 для 1Ф)
        starting_method: direct/star_delta/soft_start/VFD
    """
    # Гидравлическая мощность
    Q_m3s = Q_m3h / 3600.0
    g = 9.81
    P_hyd_kw = rho_kg_m3 * g * Q_m3s * H_m / 1000.0

    # Мощность на валу
    P_shaft_kw = P_hyd_kw / pump_efficiency

    # КПД двигателя
    eta_motor = MOTOR_EFFICIENCY_BY_CLASS.get(motor_class, 0.90)

    # Мощность двигателя
    P_motor_required = P_shaft_kw / eta_motor * safety_factor
    P_motor_nominal = round_up_to_standard(P_motor_required)

    # Номинальный ток (3Ф, 400 В типично)
    if U_v >= 380:
        I_nom = P_motor_nominal * 1000.0 / (math.sqrt(3) * U_v * cos_phi * eta_motor)
    else:
        # 1Ф
        I_nom = P_motor_nominal * 1000.0 / (U_v * cos_phi * eta_motor)

    # Кратность пускового тока
    starting_multipliers = {
        "direct": 7.0,
        "star_delta": 2.5,
        "soft_start": 2.5,
        "VFD": 1.2,
    }
    K_start = starting_multipliers.get(starting_method, 7.0)
    I_start = I_nom * K_start

    notes = [
        f"P_гидр = ρ·g·Q·H = {rho_kg_m3}·9.81·{Q_m3s:.4f}·{H_m} = {P_hyd_kw:.2f} кВт",
        f"P_вал = P_гидр/η_насос = {P_hyd_kw:.2f}/{pump_efficiency} = {P_shaft_kw:.2f} кВт",
        f"P_двиг(тр.) = P_вал/η_двиг·K = {P_shaft_kw:.2f}/{eta_motor}·{safety_factor} = {P_motor_required:.2f} кВт",
        f"P_двиг(ном.) = ближайшее стандартное ≥{P_motor_required:.2f} = {P_motor_nominal} кВт ({motor_class})",
        f"I_ном = P/(√3·U·cosφ·η) = {I_nom:.1f} А (при U={U_v} В)",
        f"I_пуск ≈ {K_start}×I_ном = {I_start:.1f} А ({starting_method})",
    ]

    return MotorPowerCalc(
        P_hydraulic_kw=round(P_hyd_kw, 2),
        P_shaft_kw=round(P_shaft_kw, 2),
        P_motor_required_kw=round(P_motor_required, 2),
        P_motor_nominal_kw=P_motor_nominal,
        pump_efficiency=pump_efficiency,
        motor_efficiency=eta_motor,
        safety_factor=safety_factor,
        nominal_current_a=round(I_nom, 1),
        starting_current_a=round(I_start, 1),
        starting_method=starting_method,
        notes=notes,
    )


def calc_full_load_current(
    P_motor_kw: float,
    U_v: int = 400,
    cos_phi: float = 0.85,
    motor_efficiency: float = 0.90,
) -> float:
    """Номинальный ток двигателя по полной мощности.

    Для трёхфазного: I = P / (√3·U·cosφ·η)
    Для однофазного: I = P / (U·cosφ·η)
    """
    if U_v >= 380:
        return P_motor_kw * 1000.0 / (math.sqrt(3) * U_v * cos_phi * motor_efficiency)
    return P_motor_kw * 1000.0 / (U_v * cos_phi * motor_efficiency)
