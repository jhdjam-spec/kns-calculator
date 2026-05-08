"""Pydantic-модели для калькулятора ливневых стоков (Phase 18)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SpRevision = Literal["SP_32_2012", "SP_32_2018"]


class SurfaceBreakdown(BaseModel):
    """Распределение площадей по типам поверхностей (га)."""

    roof_ha: float = Field(default=0.0, ge=0, description="Кровли")
    asphalt_ha: float = Field(default=0.0, ge=0, description="Асфальт/бетон")
    paving_dense_ha: float = Field(default=0.0, ge=0, description="Брусчатка плотная")
    paving_loose_ha: float = Field(default=0.0, ge=0, description="Брусчатка с расшивкой")
    gravel_ha: float = Field(default=0.0, ge=0, description="Гравий")
    crushed_stone_ha: float = Field(default=0.0, ge=0, description="Щебень")
    soil_ha: float = Field(default=0.0, ge=0, description="Утрамбованный грунт")
    lawn_ha: float = Field(default=0.0, ge=0, description="Газоны")
    forest_ha: float = Field(default=0.0, ge=0, description="Лесопарк")
    water_ha: float = Field(default=0.0, ge=0, description="Открытая вода")

    @property
    def total_ha(self) -> float:
        return (
            self.roof_ha
            + self.asphalt_ha
            + self.paving_dense_ha
            + self.paving_loose_ha
            + self.gravel_ha
            + self.crushed_stone_ha
            + self.soil_ha
            + self.lawn_ha
            + self.forest_ha
            + self.water_ha
        )


class StormInput(BaseModel):
    """Входные данные калькулятора ливневок."""

    sp_revision: SpRevision = Field(
        description=(
            "Редакция СП 32.13330. Без дефолта — пользователь обязан выбрать. "
            "'SP_32_2012' (Z_асфальт=0.28, эталоны ВБД) или 'SP_32_2018' (Z=0.33, новые проекты)."
        )
    )
    region_city: str = Field(description="Название города (для q20, n, mr из climate_db)")
    surfaces: SurfaceBreakdown = Field(description="Распределение площадей")
    period_P_year: int = Field(default=1, ge=1, le=10, description="Период повторяемости, годы (СП 32 табл.9)")

    # tcon, tcan, tp параметры (опционально — есть defaults)
    # ВНИМАНИЕ: t_concentration_min=10 по умолчанию (СП 32 §6.2.4 — типовое 5-10 мин,
    # берём верхнюю границу как консервативную оценку для незастроенной территории).
    # Калибровка по эталонам ВБД (Phase 18.1) показала: t_con=5 даёт +45-70% завышение.
    pipe_total_length_m: float = Field(default=500, ge=0, description="Общая длина трубопроводов сети")
    pipe_velocity_mps: float = Field(default=3.0, ge=0.1, le=10, description="Расчётная скорость в трубах")
    t_concentration_min: float = Field(default=10.0, ge=0, description="Время поверхностной концентрации, мин (СП 32 §6.2.4)")

    # Опционально для расчёта ЛОС
    snow_clearance_pct: float = Field(default=0.05, ge=0, le=1, description="Доля F с уборкой снега (F_y/F)")
    selective_treatment: bool = Field(default=True, description="Селективная очистка (только грязная часть)")


class AnnualVolumes(BaseModel):
    """Среднегодовые объёмы стоков (м³/год)."""

    rain_m3_year: float
    snowmelt_m3_year: float
    irrigation_m3_year: float
    total_m3_year: float


class DesignVolumes(BaseModel):
    """Расчётные суточные объёмы для очистных (м³/сут)."""

    h_a_mm: float
    psi_mid: float
    rain_design_m3_day: float
    snowmelt_design_m3_day: float
    max_for_accumulator_m3: float


class PeakFlow(BaseModel):
    """Пиковый расход Q_r."""

    Q_r_l_s: float
    t_r_min: float
    t_p_min: float
    A_param: float
    Z_mid: float
    formula: str = "Q_r = Z_mid × A^1.2 × F / t_r^(1.2n−0.1)"


class LosRecommendation(BaseModel):
    """Рекомендация по ЛОС."""

    accumulator_volume_m3: float
    los_capacity_l_s_min: float
    los_capacity_l_s_max: float
    bypass_for_clean: bool


class StormResult(BaseModel):
    """Полный результат расчёта."""

    annual: AnnualVolumes
    design: DesignVolumes
    peak: PeakFlow
    recommendation: LosRecommendation
    sp_revision_used: SpRevision = Field(description="Редакция СП 32, по которой выполнен расчёт")
    formula_ref: str = Field(
        default="СП 32.13330 §6.2.4 (Q_r = Z_mid × A^1.2 × F / t_r^(1.2n−0.1))",
        description="Ссылка на пункт норматива",
    )
    tolerance_pct: float = Field(
        default=15.0,
        description="Допуск инженерной точности (% относительно эталона)",
    )
    warnings: list[str] = Field(default_factory=list)
    region_data: dict = Field(default_factory=dict, description="Использованные параметры из climate_db")
    inputs_summary: dict = Field(default_factory=dict)
