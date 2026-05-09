"""Phase 27: Локальные очистные сооружения (ЛОС).

Источники:
- СП 32.13330.2018 §7 — Очистные сооружения канализации
- СанПиН 2.1.3684-21 — Санитарные требования
- ПП РФ № 728 (13.07.2013) — Правила сброса в централизованные системы
- ПП РФ № 644 — Договорные отношения с водоканалом
- Приказ Минсельхоза №552 (13.12.2016) — Рыбохозяйственные ПДК
- ИТС 10-2015 — Очистка сточных вод

Покрытие:
- Состав стоков по типу объекта (хозбытовые, промышленные, дождевые)
- ПДК для разных категорий сброса
- Расчёт степени очистки η = (C_in - C_out) / C_in
- Подбор ЛОС-блока по производительности
"""
from .aerotank import (
    LOAD_PROFILES,
    AerotankCalcResult,
    LoadProfile,
    calc_aerotank,
    list_load_profiles,
)
from .composition import (
    POLLUTANT_LIMITS_BY_DISCHARGE,
    TYPICAL_INFLUENT_DOMESTIC,
    PollutantConcentration,
    calc_purification_efficiency,
    typical_influent_for_object,
)
from .models import (
    DischargeCategory,
    LOSResult,
    LOSScenarioInput,
    LOSTreatmentLevel,
)
from .selection import LOS_CATALOG, select_los_block

__all__ = [
    "AerotankCalcResult",
    "DischargeCategory",
    "LOAD_PROFILES",
    "LoadProfile",
    "LOSResult",
    "LOSScenarioInput",
    "LOSTreatmentLevel",
    "LOS_CATALOG",
    "POLLUTANT_LIMITS_BY_DISCHARGE",
    "PollutantConcentration",
    "TYPICAL_INFLUENT_DOMESTIC",
    "calc_aerotank",
    "calc_purification_efficiency",
    "list_load_profiles",
    "select_los_block",
    "typical_influent_for_object",
]
