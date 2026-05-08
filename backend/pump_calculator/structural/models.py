"""Pydantic-модели для прочностных расчётов (Phase 26)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CorpusMaterial = Literal[
    "fiberglass",     # Стеклопластик / FRP
    "hdpe",           # HDPE / ПЭ-100
    "polypropylene",  # ПП
    "concrete",       # Бетон сборный
    "concrete_monolith",  # Бетон монолитный
    "steel",          # Сталь Ст3
    "stainless",      # Нержавейка AISI304/316
]


class StructuralScenarioInput(BaseModel):
    """Входные для прочностных расчётов корпуса."""

    diameter_m: float = Field(ge=0.5, description="Диаметр корпуса, м")
    height_m: float = Field(ge=1.0, description="Высота корпуса (заглубление), м")
    material: CorpusMaterial = Field(description="Материал корпуса")
    wall_thickness_mm: float = Field(default=10.0, ge=1.0, description="Существующая толщина стенки, мм")

    # Условия установки
    groundwater_depth_m: float = Field(default=2.0, description="Глубина УГВ от поверхности, м")
    burial_depth_m: float = Field(description="Глубина заложения корпуса (от поверхности до низа), м")
    soil_density_kg_m3: float = Field(default=1700, ge=1000, description="Плотность грунта, кг/м³")
    soil_friction_angle_deg: float = Field(default=30, ge=0, le=45, description="Угол внутреннего трения, °")

    # Если применимо
    contents_density_kg_m3: float = Field(default=1000, description="Плотность содержимого (вода/стоки)")
    fill_level_pct: float = Field(default=20, ge=0, le=100, description="Заполнение корпуса при расчёте всплытия, %")


class BallastResult(BaseModel):
    """Результат расчёта пригруза."""

    is_required: bool = Field(description="Требуется ли пригруз")
    archimedes_force_kn: float = Field(description="Подъёмная сила Архимеда, кН")
    self_weight_kn: float = Field(description="Собственный вес корпуса, кН")
    contents_weight_kn: float = Field(description="Вес содержимого, кН")
    friction_resistance_kn: float = Field(description="Сопротивление трения по стенкам, кН")
    safety_factor: float = Field(description="Коэф. запаса (≥1.1 по СП 32 §6.3)")

    ballast_concrete_volume_m3: float = Field(description="Расчётный объём бетона пригруза, м³")
    ballast_concrete_thickness_m: float = Field(description="Толщина бетонной плиты под корпусом, м")
    notes: list[str]
    references: list[dict]


class WallThicknessResult(BaseModel):
    """Результат расчёта толщины стенки."""

    required_thickness_mm: float
    is_current_sufficient: bool
    sn_class: str = Field(description="Класс жёсткости SN по ISO 9969 (SN2/SN4/SN8/SN16/SN32)")
    safety_margin_pct: float
    notes: list[str]


class LadderResult(BaseModel):
    """Результат расчёта лестницы."""

    n_landings: int = Field(description="Число промежуточных площадок")
    landing_heights_m: list[float] = Field(description="Высоты площадок от низа, м")
    ladder_angle_deg: float = Field(description="Угол наклона лестницы, °")
    ladder_total_length_m: float
    handrail_height_m: float = Field(default=1.1, description="Высота поручня (СП 12-04)")
    material: str = Field(description="Рекомендованный материал")
    notes: list[str]
    references: list[dict]
