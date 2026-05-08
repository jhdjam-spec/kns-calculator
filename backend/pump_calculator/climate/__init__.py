"""Phase 25: Климатические расчёты.

Источники:
- СП 131.13330.2020 — Строительная климатология
- СП 20.13330.2016 + Изм.№4 (2024) — Нагрузки и воздействия
- СП 14.13330.2018 + ОСР-2015 — Сейсмическое строительство
- СП 25.13330.2020 — Вечномёрзлые грунты
- СП 32.13330.2018 §6.5 — Глубина заложения сетей канализации

Покрытие:
- Глубина заложения трубы (от глубины промерзания + СП 32 §6.5)
- Снеговая и ветровая нагрузка на павильон
- Сейсмический коэффициент
- Утепление подводящих/напорных трасс
"""
from .frost import (
    FROST_DEPTH_BY_CITY_M,
    SOIL_FROST_FACTORS,
    calc_frost_depth_normative,
    calc_pipe_burial_depth,
)
from .loads import (
    SEISMIC_COEFFICIENTS,
    SNOW_REGION_S0_KPA,
    WIND_REGION_W0_PA,
    calc_seismic_load,
    calc_snow_load_pavilion,
    calc_wind_load_pavilion,
)
from .models import (
    ClimateLoadsResult,
    ClimateScenarioInput,
    PipeBurialResult,
)

__all__ = [
    "FROST_DEPTH_BY_CITY_M",
    "SEISMIC_COEFFICIENTS",
    "SNOW_REGION_S0_KPA",
    "SOIL_FROST_FACTORS",
    "WIND_REGION_W0_PA",
    "ClimateLoadsResult",
    "ClimateScenarioInput",
    "PipeBurialResult",
    "calc_frost_depth_normative",
    "calc_pipe_burial_depth",
    "calc_seismic_load",
    "calc_snow_load_pavilion",
    "calc_wind_load_pavilion",
]
