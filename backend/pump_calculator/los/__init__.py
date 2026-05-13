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
from .aerotank_sizing import (
    AerotankSizingResult,
    calculate_aerotank_volume,
)
from .composition import (
    POLLUTANT_LIMITS_BY_DISCHARGE,
    TYPICAL_INFLUENT_DOMESTIC,
    PollutantConcentration,
    calc_purification_efficiency,
    typical_influent_for_object,
)
from .denitrification import (
    NO3_LIMITS_BY_DISCHARGE,
    calculate_denitrification,
    get_no3_limit,
)
from .models import (
    DischargeCategory,
    LOSResult,
    LOSScenarioInput,
    LOSTreatmentLevel,
)
from .phosphorus import (
    P_DEFAULTS_BY_WASTEWATER,
    P_LIMITS_BY_DISCHARGE,
    al2so4_3_dose_mg_per_mg_p_removed,
    calculate_p_removal,
    fecl3_dose_mg_per_mg_p_removed,
    get_p_default,
    get_p_limit,
)
from .selection import LOS_CATALOG, select_los_block

__all__ = [
    "AerotankCalcResult",
    "AerotankSizingResult",
    "DischargeCategory",
    "LOAD_PROFILES",
    "LoadProfile",
    "LOSResult",
    "LOSScenarioInput",
    "LOSTreatmentLevel",
    "LOS_CATALOG",
    "NO3_LIMITS_BY_DISCHARGE",
    "P_DEFAULTS_BY_WASTEWATER",
    "P_LIMITS_BY_DISCHARGE",
    "POLLUTANT_LIMITS_BY_DISCHARGE",
    "PollutantConcentration",
    "TYPICAL_INFLUENT_DOMESTIC",
    "al2so4_3_dose_mg_per_mg_p_removed",
    "calc_aerotank",
    "calc_purification_efficiency",
    "calculate_aerotank_volume",
    "calculate_denitrification",
    "calculate_p_removal",
    "fecl3_dose_mg_per_mg_p_removed",
    "get_no3_limit",
    "get_p_default",
    "get_p_limit",
    "list_load_profiles",
    "select_los_block",
    "typical_influent_for_object",
]
