"""Phase 23: Расчёты водопотребления и подбор повысительных насосов.

Источники:
- СП 30.13330.2020 — Внутренний водопровод и канализация
- СП 31.13330.2021 — Водоснабжение. Наружные сети
- СП 399.1325800.2018 — Проектирование сетей ВК

Покрытие:
- Расчёт хозпитьевого расхода Q_сред / Q_max_сут / Q_max_час / Q_сек
- Подбор повысительной насосной станции (ВНС)
- Расчёт ёмкости резервуара хозпитьевого
- Зонирование высотных зданий (СП 30 §7.10)
"""
from .demand import (
    NORMS_LITERS_PER_DAY,
    Q_aggregate,
    calc_water_demand,
)
from .models import (
    BuildingType,
    WaterDemandResult,
    WaterScenarioInput,
    WaterStationSpec,
)
from .station import sizing_water_station

__all__ = [
    "BuildingType",
    "NORMS_LITERS_PER_DAY",
    "Q_aggregate",
    "WaterDemandResult",
    "WaterScenarioInput",
    "WaterStationSpec",
    "calc_water_demand",
    "sizing_water_station",
]
