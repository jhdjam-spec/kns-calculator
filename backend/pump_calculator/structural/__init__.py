"""Phase 26: Прочностные расчёты.

Источники:
- СП 22.13330.2016 — Основания зданий и сооружений
- СП 28.13330.2017 — Защита от коррозии
- СП 12-104-2002 — Лестницы и площадки
- ГОСТ Р 51232-98 — Пластмассовые ёмкости
- ASTM D2412 — Тест на сопротивление кольцевой деформации труб
- СП 32.13330.2018 §6.3 — Предотвращение всплытия

Покрытие:
- Пригруз бетоном при УГВ (Архимед vs G_корпуса + G_бетона + F_трения)
- Минимальная толщина стенки полимерного корпуса
- Расчёт лестниц и площадок (СП 12-04)
- Анкеровка и крепление
"""
from .ballast import (
    BallastResult,
    calc_ballast_concrete,
)
from .ground_context import GroundContext, SoilType
from .ladder import (
    LadderResult,
    calc_ladder_geometry,
)
from .lateral_pressure import (
    GAMMA_WATER_KN_M3,
    GRAVITY,
    PE100_SDR11_ADMISSIBLE_KPA,
    PE100_SDR17_ADMISSIBLE_KPA,
    LateralPressure,
    calculate_pressure,
    check_corpus_strength,
    wall_friction_force_kN,
)
from .models import (
    StructuralScenarioInput,
    WallThicknessResult,
)
from .seismic import (
    SOIL_SEISMIC_FACTORS,
    SeismicResult,
    SoilSeismicCategory,
    calc_seismic_force_on_corpus,
    list_soil_categories,
)
from .trench_stability import (
    SAFE_SLOPE_BY_DEPTH,
    SHEET_PILE_MANDATORY_DEPTH_M,
    SHEET_PILE_RECOMMENDED_DEPTH_M,
    TrenchStability,
    check_trench_stability,
)
from .wall_thickness import calc_polymer_wall_thickness

__all__ = [
    "BallastResult",
    "GAMMA_WATER_KN_M3",
    "GRAVITY",
    "GroundContext",
    "LadderResult",
    "LateralPressure",
    "PE100_SDR11_ADMISSIBLE_KPA",
    "PE100_SDR17_ADMISSIBLE_KPA",
    "SAFE_SLOPE_BY_DEPTH",
    "SHEET_PILE_MANDATORY_DEPTH_M",
    "SHEET_PILE_RECOMMENDED_DEPTH_M",
    "SOIL_SEISMIC_FACTORS",
    "SeismicResult",
    "SoilSeismicCategory",
    "SoilType",
    "StructuralScenarioInput",
    "TrenchStability",
    "WallThicknessResult",
    "calc_ballast_concrete",
    "calc_ladder_geometry",
    "calc_polymer_wall_thickness",
    "calc_seismic_force_on_corpus",
    "calculate_pressure",
    "check_corpus_strength",
    "check_trench_stability",
    "list_soil_categories",
    "wall_friction_force_kN",
]
