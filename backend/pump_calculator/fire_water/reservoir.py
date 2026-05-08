"""Расчёт пожарного резервуара по СП 8.13130.2020.

Главные положения:
- §9.1: запас воды на пожаротушение должен обеспечивать расчётное число
  одновременных пожаров и расчётное время.
- §9.4: время восстановления НЗ — не более 24 ч (общая практика), 36 ч для
  населённых пунктов до 5 000 чел. и предприятий с категориями В-Д.
- §9.7: при объёме НЗ ≥ 1000 м³ требуется не менее 2 резервуаров.

Формула:
    V_НЗ = (Q_внешний + Q_внутренний + Q_спр) × T_пож × 3.6 (л/с → м³/ч)
"""
from __future__ import annotations

from .models import FireDemand, FireScenarioInput, ReservoirSpec


def sizing_reservoir(
    inputs: FireScenarioInput,
    demand: FireDemand,
) -> tuple[ReservoirSpec, list[str]]:
    """Подбор пожарного резервуара."""
    notes: list[str] = []

    # Общий расход на одновременные пожары × расчётное время
    duration_h = inputs.fire_duration_h
    n_fires = inputs.n_fires_simultaneous

    # Объём для основных систем
    q_main_lps = demand.external_lps + demand.internal_lps
    v_main_m3 = q_main_lps * 3.6 * duration_h * n_fires

    # Объём для автомат. установок (другое время — обычно 1 ч по СП 485)
    v_sprinkler_m3 = demand.sprinkler_lps * 3.6 * inputs.sprinkler_duration_h

    v_total = v_main_m3 + v_sprinkler_m3
    notes.append(
        f"V_НЗ = (Q_внешн+Q_внутр)·3.6·T·n + Q_спр·3.6·T_спр = "
        f"({q_main_lps:.1f}·3.6·{duration_h}·{n_fires}) + ({demand.sprinkler_lps:.1f}·3.6·{inputs.sprinkler_duration_h}) "
        f"= {v_main_m3:.1f} + {v_sprinkler_m3:.1f} = {v_total:.1f} м³"
    )

    # Округление до стандартного объёма (50, 100, 150, 200, 300, 500 м³ и далее с шагом 250)
    standard_volumes = [25, 50, 100, 150, 200, 250, 300, 500, 750, 1000, 1500, 2000, 3000, 5000]
    v_standard = next((v for v in standard_volumes if v >= v_total), int((v_total // 1000 + 1) * 1000))
    notes.append(f"Округлено до стандартного: {v_standard} м³")

    # Число резервуаров — минимум 2 если V≥1000 (СП 8.13130 §9.7)
    if v_standard >= 1000:
        n_reservoirs = 2
        notes.append("V_НЗ ≥ 1000 м³ → минимум 2 резервуара (СП 8.13130 §9.7)")
    else:
        n_reservoirs = 1
        notes.append("V_НЗ < 1000 м³ → допускается 1 резервуар")

    v_per_reservoir = v_standard / n_reservoirs

    # Время восстановления (СП 8.13130 §9.4)
    refill_time_h = 24.0
    if inputs.occupancy in ("residential", "agricultural", "industrial_b", "industrial_d") and inputs.population < 5000:
        refill_time_h = 36.0
        notes.append("Время восстановления 36 ч (СП 8.13130 §9.4 — нас. пункт ≤5000 чел / кат. В-Д)")
    else:
        notes.append("Время восстановления 24 ч (СП 8.13130 §9.4)")

    # Расход насоса наполнения (м³/ч)
    refill_pump_qmin = v_standard / refill_time_h
    notes.append(f"Расход насоса наполнения ≥ {refill_pump_qmin:.1f} м³/ч")

    return ReservoirSpec(
        required_volume_m3=v_standard,
        n_reservoirs=n_reservoirs,
        volume_per_reservoir_m3=v_per_reservoir,
        refill_time_h=refill_time_h,
        refill_pump_qmin_m3h=refill_pump_qmin,
    ), notes
