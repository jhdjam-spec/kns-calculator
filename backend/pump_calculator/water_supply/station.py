"""Подбор повысительной насосной станции водоснабжения (ВНС).

Источник: СП 31.13330.2021 § 6 (структура), § 11 (трубопроводы).
"""
from __future__ import annotations

from .models import (
    WaterDemandResult,
    WaterScenarioInput,
    WaterStationSpec,
)


def sizing_water_station(
    inputs: WaterScenarioInput,
    demand: WaterDemandResult,
    H_design_m: float | None = None,
) -> WaterStationSpec:
    """Подбор повысительной насосной для хозпитьевого ВНС.

    Алгоритм:
    1. Q_расч = max(Q_max_час, Q_max_сек·3600/1000) — берём в м³/ч
    2. H_расч = высота здания×10 м/эт + 10 м (на свободный напор у крана) + 5 м потерь
    3. Число рабочих: 1 при Q≤30 м³/ч, 2-3 при больших (для устойчивого регулирования)
    4. Резерв ≥ 1 насос
    5. VFD рекомендуется при Q_max/Q_min > 2 или для энергоэффективности
    """
    notes: list[str] = []

    Q_design_m3h = demand.total_Q_max_hour_m3h

    # Расчётный напор
    if H_design_m is None:
        # Высотные здания: 10 м на этаж × этажность + минимум 10 м у самого верхнего крана + 5 м потерь
        H_design_m = inputs.floors * 3.5 + 10 + 5
        # 3.5 м на этаж (типовая высота гражданского здания)

    # Число рабочих насосов
    if Q_design_m3h <= 30:
        operating = 1
        notes.append(f"Q={Q_design_m3h:.1f} м³/ч ≤30 → 1 рабочий насос")
    elif Q_design_m3h <= 100:
        operating = 2
        notes.append(f"Q={Q_design_m3h:.1f} м³/ч 30-100 → 2 рабочих параллельно")
    else:
        operating = 3
        notes.append(f"Q={Q_design_m3h:.1f} м³/ч >100 → 3 рабочих параллельно (устойчивое регулирование)")

    pump_q_m3h = Q_design_m3h / operating
    pump_q_lps = pump_q_m3h * 1000.0 / 3600.0

    # Резерв
    standby = 1
    notes.append("Резерв ≥1 насос (СП 31.13330 §6.5)")

    # VFD
    has_vfd = False
    if Q_design_m3h > 10 or inputs.floors > 5:
        has_vfd = True
        notes.append("Рекомендуется VFD: переменная нагрузка, экономия 20-50%")

    # Гидроаккумулятор — для малых ВНС (защита от частых пусков)
    has_tank = Q_design_m3h <= 30

    # Резервуар (если источник — open_source/well, или нужен запас)
    reservoir_v = None
    if inputs.water_source in ("open_source", "well"):
        # Запас на сутки + резерв
        reservoir_v = demand.total_Q_max_day_m3 * (1 + inputs.reserve_factor)
        notes.append(
            f"Источник {inputs.water_source} → резервуар {reservoir_v:.1f} м³ "
            f"(Q_max·сут × (1+{inputs.reserve_factor}))"
        )

    # Категория надёжности (СП 31.13330 §6.5)
    if inputs.population > 50_000:
        cat = 1
    elif inputs.population > 5_000:
        cat = 2
    else:
        cat = 3
    notes.append(f"Категория надёжности {['','I','II','III'][cat]}")

    return WaterStationSpec(
        operating_pumps=operating,
        standby_pumps=standby,
        pump_q_lps=round(pump_q_lps, 3),
        pump_q_m3h=round(pump_q_m3h, 2),
        pump_h_m=round(H_design_m, 1),
        has_vfd=has_vfd,
        has_pressure_tank=has_tank,
        reservoir_volume_m3=round(reservoir_v, 1) if reservoir_v else None,
        notes=notes,
        reliability_category=cat,
    )
