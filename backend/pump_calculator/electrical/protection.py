"""Подбор автоматического выключателя по ПУЭ 3.1, 7.3.

Алгоритм:
1. I_ном_AB ≥ 1.25·I_ном_двигателя (для S1) или 1.4·I_ном (для S3)
2. Кривая срабатывания: D или K — для двигателей (отстройка от пускового тока)
3. Отключающая способность Icu — по току КЗ в точке установки
4. Класс токоограничения — для селективности с вышестоящими аппаратами
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CircuitBreakerCurve = Literal["B", "C", "D", "K", "MA"]


@dataclass
class ProtectionDevice:
    breaker_rating_a: int          # Номинальный ток автомата
    curve: CircuitBreakerCurve     # Кривая B/C/D/K/MA
    icu_ka: float                  # Отключающая способность, кА
    poles: int                     # 1P/3P/4P
    type: str                      # "MCB" | "MPCB" | "MCCB"
    description: str
    notes: list[str]


# Стандартная сетка номинальных токов автоматов (А)
STANDARD_BREAKER_RATINGS_A = [
    6, 10, 13, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250,
    315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500,
]


def select_circuit_breaker(
    I_load_a: float,
    starting_method: str = "soft_start",
    motor_duty: str = "S3",
    short_circuit_ka: float = 6.0,
    is_three_phase: bool = True,
) -> ProtectionDevice:
    """Подбор автомата для двигателя.

    Args:
        I_load_a: номинальный ток двигателя
        starting_method: direct/star_delta/soft_start/VFD
        motor_duty: S1 (длительный) или S3 (повторно-кратковременный — для КНС)
        short_circuit_ka: ожидаемый ток КЗ в точке установки, кА
        is_three_phase: 3Ф или 1Ф
    """
    notes: list[str] = []

    # Запас по току нагрузки
    if motor_duty == "S3":
        K = 1.4
        notes.append("Режим S3 — запас 1.4 (СП 6.13130 / ПУЭ 7.3.121)")
    else:
        K = 1.25
        notes.append("Режим S1 — запас 1.25")

    I_required = I_load_a * K

    # Подбираем ближайший больший
    breaker_rating = next(
        (r for r in STANDARD_BREAKER_RATINGS_A if r >= I_required),
        STANDARD_BREAKER_RATINGS_A[-1],
    )
    notes.append(f"I_расч = {I_load_a:.1f}·{K} = {I_required:.1f} А → I_ном автомата = {breaker_rating} А")

    # Кривая срабатывания
    curve_map = {
        "direct": "D",       # I_пуск = 7×I_ном — нужна D (10×I_ном) или K
        "star_delta": "C",   # I_пуск ~2.5× — хватает C (5×I_ном)
        "soft_start": "C",   # I_пуск ~2.5× — C
        "VFD": "B",          # I_пуск ~1.2× — B (3-5×I_ном)
    }
    curve = curve_map.get(starting_method, "D")
    notes.append(f"Метод пуска {starting_method} → кривая {curve}")

    # Тип автомата
    if breaker_rating <= 125:
        device_type = "MCB"  # Modular Circuit Breaker
    elif breaker_rating <= 1600:
        device_type = "MCCB"  # Molded Case Circuit Breaker
    else:
        device_type = "ACB"   # Air Circuit Breaker

    # Отключающая способность с запасом
    if short_circuit_ka <= 6:
        icu = 6
    elif short_circuit_ka <= 10:
        icu = 10
    elif short_circuit_ka <= 25:
        icu = 25
    elif short_circuit_ka <= 36:
        icu = 36
    else:
        icu = 50

    notes.append(f"I_кз ожидаемый {short_circuit_ka} кА → Icu автомата ≥ {icu} кА")

    poles = 3 if is_three_phase else 1
    description = f"{device_type} {poles}P {breaker_rating}A {curve} Icu={icu}кА"

    return ProtectionDevice(
        breaker_rating_a=breaker_rating,
        curve=curve,
        icu_ka=icu,
        poles=poles,
        type=device_type,
        description=description,
        notes=notes,
    )
