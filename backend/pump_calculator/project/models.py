"""Pydantic-модели для главного flow «Проект»."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ProjectPreset = Literal[
    "ihs",                  # ИЖС / частный дом
    "kotedj_settlement",    # Коттеджный посёлок
    "apartment_complex",    # Многоквартирный ЖК
    "hotel",                # Гостиница
    "trc",                  # ТРЦ / БЦ
    "azs",                  # АЗС / автомойка
    "industrial",           # Промпредприятие
    "warehouse",            # Склад
    "gazprom",              # Газпром / нефтегазовый
    "agricultural",         # Сельхоз
    "school",               # Школа / детсад
    "hospital",             # Больница
    "custom",               # Произвольный
]


class ProjectSubsystems(BaseModel):
    """Какие подсистемы нужно рассчитать."""

    kns: bool = Field(default=True, description="КНС (канализационная)")
    vns_potable: bool = Field(default=False, description="ВНС хозпитьевая")
    vns_fire: bool = Field(default=False, description="ВНС пожарная")
    storm: bool = Field(default=False, description="Ливневая канализация")
    los: bool = Field(default=False, description="Локальные очистные")
    electrical: bool = Field(default=True, description="Электрика и шкаф")
    climate: bool = Field(default=True, description="Климатические нагрузки")
    structural: bool = Field(default=True, description="Прочность корпуса")
    bom_export: bool = Field(default=True, description="Сводная BOM")


class ProjectInput(BaseModel):
    """Входные данные проекта (минимальный режим — 5-7 полей)."""

    project_name: str
    project_code: str = ""
    customer: str = ""
    preset: ProjectPreset = "ihs"

    # Локация (для climate, storm, fire)
    region_city: str = "Краснодар"

    # Базовые параметры
    population: int = Field(default=4, ge=0, description="Расчётное число пользователей (жители/сотрудники)")
    floors: int = Field(default=1, ge=1)
    volume_m3: float = Field(default=500, ge=0, description="Объём здания, м³")
    area_m2: float = Field(default=200, ge=0, description="Площадь территории, м²")
    rooms: int = Field(default=0, ge=0, description="Число номеров (для гостиниц)")
    beds: int = Field(default=0, ge=0, description="Число коек (для больниц)")
    visits_per_day: int = Field(default=0, ge=0, description="Посещений в сутки (поликлиники, кафе)")

    # Подсистемы
    subsystems: ProjectSubsystems = ProjectSubsystems()

    # Опциональные параметры
    has_groundwater: bool = False
    soil_type: str = "clay_loam"
    is_atex_zone: bool = False


class SubsystemResult(BaseModel):
    """Результат одного расчёта в проекте."""

    name: str
    status: Literal["ok", "warning", "skipped", "error"]
    summary: str            # 1-2 предложения для UI карточки
    data: dict              # Полный результат расчёта
    references: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProjectResult(BaseModel):
    """Сводный результат проекта со всеми подсистемами."""

    project_name: str
    project_code: str
    preset: ProjectPreset

    # Результаты по подсистемам
    kns: SubsystemResult | None = None
    vns_potable: SubsystemResult | None = None
    vns_fire: SubsystemResult | None = None
    storm: SubsystemResult | None = None
    los: SubsystemResult | None = None
    electrical: SubsystemResult | None = None
    climate: SubsystemResult | None = None
    structural: SubsystemResult | None = None

    # Сводка
    total_estimated_cost_rub: float = 0
    total_warnings: int = 0
    bom: list[dict] = Field(default_factory=list)
    references_consolidated: list[dict] = Field(default_factory=list)

    notes: list[str]
