"""Pydantic-модели для расчёта ЛОС (Phase 27)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Тип источника стоков
SourceType = Literal[
    "domestic",            # Хозбытовые
    "industrial_food",     # Пищевая промышленность (мясо, молоко)
    "industrial_oily",     # АЗС, автомойки, нефтебаза
    "industrial_chemical", # Гальваника, химическая
    "stormwater",          # Дождевые
    "leachate_landfill",   # Фильтрат свалок ТКО
    "agricultural",        # С/х (полив, навоз)
]

# Категория точки сброса очищенных стоков
DischargeCategory = Literal[
    "central_sewerage",    # В центральную канализацию (ПП-728)
    "ground_water",        # Подземное складирование (рассеивание)
    "fishery_water",       # Рыбохозяйственный водоём (Приказ МСХ-552 — самые строгие)
    "drinking_source",     # Водоём питьевого назначения (СанПиН 2.1.5.980)
    "household_source",    # Водоём хозяйственно-бытового использования
    "irrigation",          # Использование на полив (по СанПиН после доочистки)
]

# Уровень очистки
LOSTreatmentLevel = Literal[
    "mechanical",        # Только механика (решётки, отстойники, песколовки)
    "biological",        # Механика + биология (БПК -90-95%)
    "deep_treatment",    # + доочистка (фильтры, УФ, нанофильтр)
    "advanced",          # + RO/MBR/специфические для tough стоков
]


class PollutantConcentration(BaseModel):
    """Концентрации загрязнителей, мг/л."""

    bod5: float = Field(default=0, description="БПК₅, мг/л О₂")
    cod: float = Field(default=0, description="ХПК, мг/л О₂")
    suspended_solids: float = Field(default=0, description="Взвешенные вещества SS, мг/л")
    nh4_n: float = Field(default=0, description="Аммонийный азот NH4-N, мг/л")
    no3_n: float = Field(default=0, description="Нитраты NO3-N, мг/л")
    po4_p: float = Field(default=0, description="Фосфаты PO4-P, мг/л")
    oil_products: float = Field(default=0, description="Нефтепродукты, мг/л")
    surfactants: float = Field(default=0, description="СПАВ, мг/л")
    fats: float = Field(default=0, description="Жиры, мг/л")
    ph: float = Field(default=7.0, description="pH")


class LOSScenarioInput(BaseModel):
    """Входные для подбора ЛОС."""

    source_type: SourceType = Field(description="Тип источника стоков")
    flow_m3_per_day: float = Field(ge=0, description="Расход, м³/сут")
    discharge_category: DischargeCategory = Field(description="Куда сбрасываем очищенные стоки")
    population_equivalent: int = Field(default=0, ge=0, description="Эквивалентная численность (для бытовых)")

    # Опционально — состав стоков на входе
    custom_influent: PollutantConcentration | None = None


class LOSBlock(BaseModel):
    """Спецификация ЛОС-блока (производитель + модель + цена)."""

    manufacturer: str
    model: str
    capacity_m3_per_day: float
    capacity_population_equivalent: int
    technology: LOSTreatmentLevel
    estimated_price_rub_2026: tuple[int, int]
    typical_purification_pct: dict[str, float] = Field(description="Типовая степень очистки по показателям, %")
    notes: list[str] = Field(default_factory=list)


class LOSResult(BaseModel):
    """Результат расчёта ЛОС."""

    influent: PollutantConcentration
    effluent_target: PollutantConcentration  # Целевые после очистки
    purification_required_pct: dict[str, float]  # Требуемая степень очистки
    treatment_level: LOSTreatmentLevel
    selected_block: LOSBlock | None = None
    candidate_blocks: list[LOSBlock] = Field(default_factory=list)
    notes: list[str]
    warnings: list[str] = Field(default_factory=list)
    references: list[dict]
