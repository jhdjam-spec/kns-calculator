"""Pydantic-модели для калькулятора противопожарного водоснабжения (Phase 22).

Источники: СП 8.13130.2020, СП 10.13130.2020.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Типы зданий по функциональному назначению (СП 8.13130 табл. 1).
OccupancyType = Literal[
    "residential",       # Жилые
    "public",            # Общественные
    "industrial_a",      # Производственные категории А, Б (горючие)
    "industrial_b",      # Производственные категории В1-В4
    "industrial_d",      # Производственные категории Д (негорючие)
    "warehouse",         # Складские
    "garage",            # Гаражи и автостоянки
    "agricultural",      # Сельскохозяйственные
]

# Степень огнестойкости / класс конструктивной пожарной опасности (123-ФЗ).
BuildingClass = Literal[
    "I",      # I-II степень огнестойкости (несгораемые)
    "III",    # III степень
    "IV",     # IV-V степень (сгораемые)
]

# Способ хранения / источник: резервуар, ВЗУ, городская сеть.
WaterSource = Literal["reservoir", "city_network", "natural_source"]


class FireScenarioInput(BaseModel):
    """Входные данные для расчёта противопожарного водоснабжения.

    Используется для одного объекта (здания или группы).
    """

    occupancy: OccupancyType = Field(description="Функциональное назначение")
    building_class: BuildingClass = Field(default="I", description="Степень огнестойкости")
    volume_m3: float = Field(ge=0, description="Объём здания, м³ (для табл. 1, 2 СП 8.13130)")
    height_m: float = Field(default=0.0, ge=0, description="Высота здания, м (≥17 м → внутренний ППВ обязателен)")
    floors: int = Field(default=1, ge=1, description="Этажность")
    population: int = Field(default=0, ge=0, description="Расчётное количество жителей (для жилых)")

    # Параметры пожара
    n_fires_simultaneous: int = Field(default=1, ge=1, description="Расчётное число одновременных пожаров")
    fire_duration_h: float = Field(default=3.0, ge=0.5, description="Расчётное время пожаротушения, ч (СП 8.13130 §6.3)")

    # Внутреннее пожаротушение
    has_internal_system: bool = Field(default=False, description="Есть ли внутренний ППВ")
    n_jets_internal: int = Field(default=2, ge=0, description="Число расчётных струй внутреннего ППВ")
    jet_flow_lps: float = Field(default=2.6, ge=0, description="Расход одной струи, л/с")

    # Источник
    water_source: WaterSource = Field(default="reservoir", description="Источник водоснабжения")

    # Дополнительно: автомат. установки (спринклеры, дренчер) — упрощённая модель
    sprinkler_flow_lps: float = Field(default=0.0, ge=0, description="Расход спринклеров, л/с (если установка есть)")
    sprinkler_duration_h: float = Field(default=1.0, ge=0, description="Время работы установки, ч")


class FireDemand(BaseModel):
    """Расходы на пожаротушение."""

    external_lps: float = Field(description="Наружное пожаротушение, л/с")
    internal_lps: float = Field(description="Внутреннее пожаротушение, л/с")
    sprinkler_lps: float = Field(description="Автомат. установки, л/с")
    total_lps: float = Field(description="Суммарный расчётный расход, л/с")
    total_m3h: float = Field(description="То же в м³/ч")
    source_table: str = Field(description="Ссылка на источник (СП 8.13130 табл. X)")


class ReservoirSpec(BaseModel):
    """Параметры пожарного резервуара."""

    required_volume_m3: float = Field(description="Расчётный объём НЗ, м³")
    n_reservoirs: int = Field(description="Минимальное число резервуаров (≥2 если объём >5000)")
    volume_per_reservoir_m3: float = Field(description="Объём одного, м³")
    refill_time_h: float = Field(description="Допустимое время восстановления, ч (СП 8.13130 §9.4)")
    refill_pump_qmin_m3h: float = Field(description="Мин. расход насоса наполнения, м³/ч")


class PumpStationSpec(BaseModel):
    """Параметры насосной станции пожаротушения."""

    operating_pumps: int = Field(description="Число рабочих насосов")
    standby_pumps: int = Field(description="Число резервных насосов (≥1 по СП 8.13130 §10)")
    pump_q_lps: float = Field(description="Расход одного насоса, л/с")
    pump_h_m: float = Field(description="Напор расчётный, м")
    pump_q_m3h: float = Field(description="Расход одного насоса, м³/ч")
    reliability_category: int = Field(description="I/II/III категория надёжности (СП 8.13130 §6.6)")
    notes: list[str] = Field(default_factory=list, description="Замечания, ссылки на пункты СП")


class RegulationRefDict(BaseModel):
    """Сериализуемая ссылка на норматив (для FireResult.references)."""

    regulation_code: str
    section: str
    purpose: str
    quote: str = ""
    url: str = ""


class FireResult(BaseModel):
    """Результат расчёта."""

    demand: FireDemand
    reservoir: ReservoirSpec | None = None
    pump_station: PumpStationSpec
    references: list[RegulationRefDict] = Field(description="Ссылки на пункты СП")
    warnings: list[str] = Field(default_factory=list, description="Предупреждения")
    inputs_echo: FireScenarioInput
