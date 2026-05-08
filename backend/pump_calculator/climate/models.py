"""Pydantic-модели для климатических расчётов (Phase 25)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SoilType = Literal[
    "sand_dry",          # Песок сухой / гравий
    "sand_wet",          # Песок водонасыщенный
    "clay_loam",         # Суглинок
    "clay",              # Глина
    "rocky",             # Скальный
    "peat",              # Торф / органика
]

PavilionRoofShape = Literal["flat", "single_pitch", "double_pitch"]


class ClimateScenarioInput(BaseModel):
    """Входные данные для климатических расчётов."""

    region_city: str = Field(description="Город (для выборки из БД промерзания и климат. района)")

    # Грунт
    soil_type: SoilType = Field(description="Тип грунта на площадке")
    has_groundwater: bool = Field(default=False, description="Высокий УГВ (<1 м от поверхности)")

    # Геометрия объекта
    pavilion_area_m2: float = Field(default=0.0, ge=0, description="Площадь крыши павильона, м²")
    pavilion_height_m: float = Field(default=3.0, ge=0, description="Высота павильона, м")
    pavilion_roof_shape: PavilionRoofShape = Field(default="flat")

    # Сейсмика (если строим в опасной зоне)
    seismic_intensity_balls: int = Field(default=6, ge=4, le=10, description="Сейсмичность площадки, баллы (СП 14)")

    # Дополнительно
    pipe_dn_mm: float = Field(default=200, ge=50, description="DN трубопровода для расчёта глубины заложения")
    pipe_above_supply_water: bool = Field(default=False, description="Трубопровод ниже водопровода (требует доп. защиты)")


class PipeBurialResult(BaseModel):
    """Результат расчёта глубины заложения трубы."""

    burial_depth_m: float = Field(description="Глубина заложения от поверхности до низа трубы, м")
    frost_depth_normative_m: float = Field(description="Нормативная глубина промерзания, м")
    frost_depth_actual_m: float = Field(description="Расчётная глубина промерзания (с учётом грунта), м")
    insulation_required: bool = Field(description="Требуется ли утепление")
    insulation_thickness_mm: float = Field(default=0, description="Рекомендуемая толщина утепления, мм")
    notes: list[str]
    references: list[dict]


class ClimateLoadsResult(BaseModel):
    """Результат расчёта климатических нагрузок на павильон."""

    snow_load_kn_m2: float = Field(description="Снеговая нагрузка S, кН/м²")
    snow_total_kn: float = Field(description="Общий снеговой груз, кН")
    snow_region: str = Field(description="Снеговой район I-VIII (СП 20 карта 1)")

    wind_load_pa: float = Field(description="Ветровая нагрузка w_0, Па")
    wind_total_kn: float = Field(description="Общая ветровая, кН")
    wind_region: str = Field(description="Ветровой район I-VII (СП 20 карта 3)")

    seismic_coefficient: float = Field(description="Расчётный коэффициент K_сейсм")
    seismic_force_kn: float = Field(description="Сейсмическая сила, кН")

    notes: list[str]
    references: list[dict]
