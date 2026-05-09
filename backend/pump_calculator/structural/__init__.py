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
from .ladder import (
    LadderResult,
    calc_ladder_geometry,
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
from .wall_thickness import calc_polymer_wall_thickness

__all__ = [
    "BallastResult",
    "LadderResult",
    "SOIL_SEISMIC_FACTORS",
    "SeismicResult",
    "SoilSeismicCategory",
    "StructuralScenarioInput",
    "WallThicknessResult",
    "calc_ballast_concrete",
    "calc_ladder_geometry",
    "calc_polymer_wall_thickness",
    "calc_seismic_force_on_corpus",
    "list_soil_categories",
]
