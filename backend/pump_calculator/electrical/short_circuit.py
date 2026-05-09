"""Расчёт тока трёхфазного короткого замыкания (ток КЗ) по упрощённой методике
ГОСТ Р 50571.5.54-2013 / ПУЭ 1.4.

Для подбора Icu автомата важно знать ожидаемый ток КЗ в точке установки.

Упрощённый расчёт:
    I_кз = U_лин / (√3 × Z_сум)

Где Z_сум = √((R_тр + R_каб)² + (X_тр + X_каб)²)

Типовые значения для распределительного трансформатора 10/0.4 кВ:
- 250 кВА: R=12 мОм, X=22 мОм → I_кз_шины ≈ 9.2 кА
- 400 кВА: R=8 мОм, X=15 мОм → I_кз_шины ≈ 13.6 кА
- 630 кВА: R=5 мОм, X=10 мОм → I_кз_шины ≈ 20.7 кА
- 1000 кВА: R=3 мОм, X=7 мОм → I_кз_шины ≈ 30.4 кА
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .cable import COPPER_R_OHM_KM, COPPER_X_OHM_KM

# Типовые сопротивления распределительных трансформаторов 10/0.4 кВ (мОм)
# по ГОСТ 11920-93 + табл. 1.9.5 ПУЭ
TRANSFORMER_IMPEDANCES_MOHM: dict[int, dict[str, float]] = {
    100: {"R": 28.0, "X": 51.0},
    160: {"R": 18.0, "X": 33.0},
    250: {"R": 12.0, "X": 22.0},
    400: {"R": 8.0, "X": 15.0},
    630: {"R": 5.0, "X": 10.0},
    1000: {"R": 3.0, "X": 7.0},
    1600: {"R": 2.0, "X": 4.5},
    2500: {"R": 1.2, "X": 3.0},
}


@dataclass
class ShortCircuitCalc:
    """Результат расчёта тока КЗ."""

    transformer_kva: int
    cable_length_m: float
    cable_section_mm2: float
    R_total_mohm: float
    X_total_mohm: float
    Z_total_mohm: float
    I_kz_ka: float
    recommended_icu_ka: int
    notes: list[str]


def calc_short_circuit(
    transformer_kva: int,
    cable_length_m: float = 0.0,
    cable_section_mm2: float = 50.0,
    U_ph_v: int = 400,
) -> ShortCircuitCalc:
    """Расчёт ожидаемого тока трёхфазного КЗ в точке установки автомата."""
    notes: list[str] = []

    # Сопротивление трансформатора
    if transformer_kva not in TRANSFORMER_IMPEDANCES_MOHM:
        kvas = sorted(TRANSFORMER_IMPEDANCES_MOHM.keys())
        nearest = min(kvas, key=lambda k: abs(k - transformer_kva))
        notes.append(
            f"Мощность трансформатора {transformer_kva} кВА не в стандартной сетке, "
            f"используем ближайший: {nearest} кВА"
        )
        transformer_kva = nearest

    z_tr = TRANSFORMER_IMPEDANCES_MOHM[transformer_kva]
    R_tr = z_tr["R"]
    X_tr = z_tr["X"]
    notes.append(f"Трансформатор {transformer_kva} кВА: R={R_tr} мОм, X={X_tr} мОм")

    # Сопротивление кабеля
    if cable_length_m > 0 and cable_section_mm2 in COPPER_R_OHM_KM:
        # COPPER_R_OHM_KM содержит Ом/км, переводим в мОм
        R_cable = COPPER_R_OHM_KM[cable_section_mm2] * cable_length_m
        X_cable = COPPER_X_OHM_KM * cable_length_m
        notes.append(
            f"Кабель {cable_section_mm2} мм² × {cable_length_m} м: "
            f"R={R_cable:.2f} мОм, X={X_cable:.2f} мОм"
        )
    else:
        R_cable = 0.0
        X_cable = 0.0
        notes.append("КЗ на шинах ТП (без кабеля)")

    R_sum = R_tr + R_cable
    X_sum = X_tr + X_cable
    Z_sum = math.sqrt(R_sum ** 2 + X_sum ** 2)

    # I_кз = U_лин / (√3 × Z_сум) [Z в Ом]
    Z_ohm = Z_sum / 1000
    I_kz_a = U_ph_v / (math.sqrt(3) * Z_ohm)
    I_kz_ka = I_kz_a / 1000

    notes.append(f"Z_сум = √(R²+X²) = √({R_sum:.1f}²+{X_sum:.1f}²) = {Z_sum:.1f} мОм")
    notes.append(
        f"I_кз = U/(√3·Z) = {U_ph_v}/(√3·{Z_ohm:.4f}) = {I_kz_ka:.1f} кА"
    )

    # Icu — ближайшее стандартное с запасом 25%
    standard_icu = [6, 10, 16, 25, 36, 50, 70, 100]
    target = I_kz_ka * 1.25
    recommended = next((i for i in standard_icu if i >= target), 100)
    notes.append(
        f"Icu автомата ≥ {target:.1f} кА (запас 25%) → выбрана {recommended} кА"
    )

    return ShortCircuitCalc(
        transformer_kva=transformer_kva,
        cable_length_m=cable_length_m,
        cable_section_mm2=cable_section_mm2,
        R_total_mohm=round(R_sum, 2),
        X_total_mohm=round(X_sum, 2),
        Z_total_mohm=round(Z_sum, 2),
        I_kz_ka=round(I_kz_ka, 2),
        recommended_icu_ka=recommended,
        notes=notes,
    )
