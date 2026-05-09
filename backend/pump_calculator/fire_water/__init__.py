"""Phase 22: Расчёты противопожарного водоснабжения.

Источники:
- СП 8.13130.2020 — Источники наружного противопожарного водоснабжения
- СП 10.13130.2020 — Внутренний противопожарный водопровод
- СП 30.13330.2020 — Внутренний водопровод и канализация (общие требования)

Модуль покрывает:
- Расчёт расхода на наружное пожаротушение по СП 8.13130 табл. 1, 2
- Расчёт расхода на внутреннее пожаротушение по СП 10.13130 табл. 1, 2
- Расчёт пожарного резервуара (объём, время восстановления)
- Подбор пожарного насоса (рабочий + резервный)
"""
from .external import calc_external_demand
from .internal import calc_internal_demand
from .models import (
    BuildingClass,
    FireDemand,
    FireResult,
    FireScenarioInput,
    OccupancyType,
    PumpStationSpec,
    ReservoirSpec,
)
from .pump_station import sizing_fire_pump_station
from .reservoir import sizing_reservoir
from .scenario import calculate_fire_scenario
from .sprinklers import (
    SPRINKLER_GROUPS,
    SprinklerCalcResult,
    SprinklerGroup,
    calc_sprinkler_demand,
    list_sprinkler_groups,
)

__all__ = [
    "BuildingClass",
    "FireDemand",
    "FireResult",
    "FireScenarioInput",
    "OccupancyType",
    "PumpStationSpec",
    "ReservoirSpec",
    "SPRINKLER_GROUPS",
    "SprinklerCalcResult",
    "SprinklerGroup",
    "calc_external_demand",
    "calc_internal_demand",
    "calc_sprinkler_demand",
    "calculate_fire_scenario",
    "list_sprinkler_groups",
    "sizing_fire_pump_station",
    "sizing_reservoir",
]
