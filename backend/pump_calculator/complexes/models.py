"""Pydantic-модели для многообъектных комплексов (Phase 29)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ObjectKind = Literal[
    "kns_household",     # КНС хозбытовая
    "kns_drainage",      # КНС ливневая
    "kns_industrial",    # КНС промышленная
    "vns_potable",       # ВНС хозпитьевая
    "vns_fire",          # ВНС пожарная
    "los",               # Локальные очистные
    "treatment_kos",     # КОС магистральные
    "reservoir",         # Резервуар
    "pavilion",          # Павильон / технический блок
]


class ObjectInComplex(BaseModel):
    """Один объект (КНС/ВНС/ЛОС) в составе комплекса."""

    object_id: str = Field(description="Уникальный идентификатор в рамках комплекса (КНС-1, ВНС-А)")
    object_kind: ObjectKind
    name: str = Field(default="", description="Полное название объекта")

    Q_m3h: float = Field(default=0, description="Расход, м³/ч")
    H_m: float = Field(default=0, description="Напор, м")

    # Ссылки на расчёты (заполняются после прогона)
    pump_selection: dict = Field(default_factory=dict)
    bom: list[dict] = Field(default_factory=list)
    estimated_cost_rub: float = Field(default=0)

    notes: list[str] = Field(default_factory=list)


class Site(BaseModel):
    """Площадка в составе комплекса (например, КС-14 имеет 5 площадок)."""

    site_id: str
    name: str
    address: str = ""
    objects: list[ObjectInComplex] = Field(default_factory=list)


class Complex(BaseModel):
    """Многообъектный комплекс (РЭУ / промплощадка / посёлок)."""

    code: str = Field(description="Шифр комплекса (КС-14, ВБ-Кубань, и т.п.)")
    name: str
    customer: str = ""
    region: str = ""
    sites: list[Site] = Field(default_factory=list)

    @property
    def total_objects(self) -> int:
        return sum(len(s.objects) for s in self.sites)

    @property
    def total_estimated_cost_rub(self) -> float:
        return sum(
            obj.estimated_cost_rub
            for site in self.sites
            for obj in site.objects
        )


class ComplexInput(BaseModel):
    """Минимальный вход для генерации комплекса (для тестов)."""

    code: str
    name: str
    sites_count: int = 1
    objects_per_site: int = 1


class ComplexBOMSummary(BaseModel):
    """Сводная спецификация комплекса."""

    complex_code: str
    complex_name: str
    total_objects: int
    total_sites: int
    total_cost_rub: float
    cost_breakdown_by_kind: dict[str, float] = Field(description="Стоимость по типам объектов")
    bom_consolidated: list[dict] = Field(description="Сводная BOM с группировкой повторов")
    notes: list[str]
