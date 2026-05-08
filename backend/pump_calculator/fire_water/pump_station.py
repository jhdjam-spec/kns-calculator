"""Подбор пожарной насосной станции по СП 8.13130 / СП 10.13130.

Главные положения:
- СП 10.13130 §6.2: 1 рабочий + 1 резервный обязательно для внутренних ППВ.
- СП 8.13130 §10: число рабочих по расчётному расходу, резерв ≥ 1.
- СП 8.13130 §6.6: категория надёжности I (АВР) — для крупных и опасных,
  II — для средних, III — для малых.

Расчётный напор (для подбора):
- Внешнее пожаротушение: 10 м у самого удалённого гидранта (СП 8.13130 §5.4)
- Внутреннее: 10 м у пожарного крана + потери (СП 10.13130 §4.5)
"""
from __future__ import annotations

from .models import FireDemand, FireScenarioInput, PumpStationSpec


def _required_reliability(inputs: FireScenarioInput) -> int:
    """Категория надёжности по СП 8.13130 §6.6."""
    # I категория — крупные и опасные объекты, нет перерывов в подаче
    if inputs.occupancy in ("industrial_a",):
        return 1
    if inputs.population > 50000:
        return 1
    if inputs.volume_m3 > 50000:
        return 1
    # II категория — средние
    if inputs.occupancy in ("industrial_b", "warehouse", "public", "garage"):
        return 2
    if inputs.population > 5000:
        return 2
    # III категория — малые
    return 3


def sizing_fire_pump_station(
    inputs: FireScenarioInput,
    demand: FireDemand,
    H_design_m: float = 60.0,
) -> tuple[PumpStationSpec, list[str]]:
    """Подбор насосной станции пожаротушения.

    Args:
        H_design_m: расчётный напор (по умолчанию 60 м — типовой для ВПВ
                    с учётом высоты здания и потерь).
    """
    notes: list[str] = []

    # Полный расход на станцию
    Q_total_lps = demand.total_lps

    # Базовое решение: 1 рабочий насос на всю производительность + 1 резерв (СП 10.13130 §6.2).
    # Для крупных систем (Q > 50 л/с) разбиваем на 2-3 рабочих параллельно для надёжности.
    if Q_total_lps > 50:
        operating_pumps = 2
        pump_q_lps = Q_total_lps / operating_pumps
        notes.append(f"Q={Q_total_lps:.1f} л/с >50 → 2 рабочих × {pump_q_lps:.1f} л/с (параллельно)")
    elif Q_total_lps > 100:
        operating_pumps = 3
        pump_q_lps = Q_total_lps / operating_pumps
        notes.append(f"Q={Q_total_lps:.1f} л/с >100 → 3 рабочих × {pump_q_lps:.1f} л/с")
    else:
        operating_pumps = 1
        pump_q_lps = Q_total_lps
        notes.append(f"Q={Q_total_lps:.1f} л/с ≤50 → 1 рабочий насос")

    # Резерв обязательно ≥1 (СП 10.13130 §6.2, СП 8.13130 §10.1)
    standby_pumps = 1
    if operating_pumps >= 2:
        standby_pumps = 1  # для 2-3 рабочих — обычно 1 резерв
    notes.append("Резерв ≥1 насос (СП 10.13130 §6.2 / СП 8.13130 §10.1)")

    # Категория надёжности
    cat = _required_reliability(inputs)
    if cat == 1:
        notes.append("Категория надёжности I — обязателен АВР, 2 независимых источника питания (СП 8.13130 §6.6)")
    elif cat == 2:
        notes.append("Категория надёжности II — допускается ручное переключение")
    else:
        notes.append("Категория надёжности III — упрощённое электроснабжение")

    pump_q_m3h = pump_q_lps * 3.6

    return PumpStationSpec(
        operating_pumps=operating_pumps,
        standby_pumps=standby_pumps,
        pump_q_lps=pump_q_lps,
        pump_q_m3h=pump_q_m3h,
        pump_h_m=H_design_m,
        reliability_category=cat,
        notes=notes,
    ), notes
