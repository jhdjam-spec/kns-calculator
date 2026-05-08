"""Построитель полной спецификации (BOM) для проекта.

Объединяет результаты всех Phase в единый список позиций с артикулами,
группировкой по разделам и суммарной стоимостью.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BOMSection = Literal[
    "pumps",            # Насосы
    "corpus",           # Корпус КНС/НС
    "control_panel",    # Шкаф управления
    "piping",           # Обвязка (трубы, арматура, фитинги)
    "automation",       # КИПиА (датчики, расходомеры)
    "electrical",       # Кабели, автоматы, заземление
    "ladder",           # Лестницы и площадки
    "ballast",          # Бетонный пригруз
    "insulation",       # Утепление
    "los",              # ЛОС-блок
    "fire_water",       # Пожарка (резервуары, насосы)
    "miscellaneous",    # Прочее
]


class BOMItem(BaseModel):
    """Одна строка спецификации."""

    section: BOMSection
    position_no: int = Field(default=0, description="Номер позиции в спеке")
    name: str
    article: str = Field(default="", description="Артикул производителя")
    manufacturer: str = Field(default="")
    quantity: float = Field(default=1)
    units: str = Field(default="шт")
    price_rub_2026: float = Field(default=0)
    lead_time_days: int = Field(default=0, description="Срок поставки, дней")
    supplier: str = Field(default="")
    source_url: str = Field(default="", description="Ссылка на каталог/прайс")
    note: str = Field(default="")

    @property
    def total_rub(self) -> float:
        return self.quantity * self.price_rub_2026


class BOMSpecification(BaseModel):
    """Полная спецификация проекта."""

    project_code: str = Field(default="")
    project_name: str = Field(default="")
    items: list[BOMItem] = Field(default_factory=list)

    @property
    def total_rub(self) -> float:
        return sum(i.total_rub for i in self.items)

    @property
    def by_section(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for item in self.items:
            result.setdefault(item.section, 0)
            result[item.section] += item.total_rub
        return result


def build_full_bom(
    project_code: str = "",
    project_name: str = "",
    pump_selection: dict | None = None,
    corpus_spec: dict | None = None,
    control_panel: dict | None = None,
    cable_selection: dict | None = None,
    fire_water_result: dict | None = None,
    los_result: dict | None = None,
    ballast_result: dict | None = None,
    climate_result: dict | None = None,
) -> BOMSpecification:
    """Собирает BOM из результатов всех расчётных модулей.

    Каждый модуль возвращает свой dict с подобранным оборудованием.
    Здесь мы преобразуем их в унифицированные BOMItem.
    """
    items: list[BOMItem] = []
    pos = 1

    # 1. Насос
    if pump_selection:
        items.append(BOMItem(
            section="pumps",
            position_no=pos,
            name=pump_selection.get("name", "Насос погружной"),
            article=pump_selection.get("article", ""),
            manufacturer=pump_selection.get("manufacturer", ""),
            quantity=pump_selection.get("quantity", 2),
            units="шт",
            price_rub_2026=pump_selection.get("price_rub_2026", 0),
            note="1 рабочий + 1 резервный (СП 32 §6.2)",
        ))
        pos += 1

    # 2. Корпус
    if corpus_spec:
        items.append(BOMItem(
            section="corpus",
            position_no=pos,
            name=corpus_spec.get("name", "Корпус КНС"),
            article=corpus_spec.get("article", ""),
            manufacturer=corpus_spec.get("manufacturer", ""),
            quantity=1,
            units="шт",
            price_rub_2026=corpus_spec.get("price_rub_2026", 0),
            note=f"D={corpus_spec.get('diameter_mm', 0)}, H={corpus_spec.get('height_mm', 0)}",
        ))
        pos += 1

    # 3. Шкаф
    if control_panel:
        avg_price = sum(control_panel.get("estimated_price_rub_2026", (0, 0))) / 2
        items.append(BOMItem(
            section="control_panel",
            position_no=pos,
            name=control_panel.get("name", "Шкаф управления"),
            quantity=1,
            units="шт",
            price_rub_2026=avg_price,
            note=control_panel.get("level", ""),
        ))
        pos += 1

    # 4. Кабель
    if cable_selection:
        items.append(BOMItem(
            section="electrical",
            position_no=pos,
            name=f"Кабель {cable_selection.get('cable_type', 'ВВГнг(А)-LS')} "
                 f"{cable_selection.get('n_cores', 4)}×{cable_selection.get('section_mm2', 2.5)}",
            quantity=cable_selection.get("length_m", 50),
            units="м",
            price_rub_2026=cable_selection.get("price_per_m", 200),
        ))
        pos += 1

    # 5. Пожарный резервуар
    if fire_water_result and fire_water_result.get("reservoir"):
        res = fire_water_result["reservoir"]
        items.append(BOMItem(
            section="fire_water",
            position_no=pos,
            name=f"Резервуар пожарный V={res.get('required_volume_m3', 0):.0f} м³",
            quantity=res.get("n_reservoirs", 1),
            units="шт",
            price_rub_2026=400_000,  # ориентир для стеклопластикового резервуара
            note=f"V_шт = {res.get('volume_per_reservoir_m3', 0):.0f} м³",
        ))
        pos += 1

    # 6. ЛОС-блок
    if los_result and los_result.get("selected_block"):
        block = los_result["selected_block"]
        avg_price = sum(block.get("estimated_price_rub_2026", (0, 0))) / 2
        items.append(BOMItem(
            section="los",
            position_no=pos,
            name=f"{block.get('manufacturer', '')} {block.get('model', '')}",
            manufacturer=block.get("manufacturer", ""),
            quantity=1,
            units="комплект",
            price_rub_2026=avg_price,
            note=f"Q={block.get('capacity_m3_per_day', 0)} м³/сут",
        ))
        pos += 1

    # 7. Бетонный пригруз
    if ballast_result and ballast_result.get("is_required"):
        v = ballast_result.get("ballast_concrete_volume_m3", 0)
        items.append(BOMItem(
            section="ballast",
            position_no=pos,
            name="Бетон В20 для пригруза корпуса",
            quantity=v,
            units="м³",
            price_rub_2026=8_500,  # типовая цена м³ бетона В20 в РФ 2026
            note=f"Толщина плиты {ballast_result.get('ballast_concrete_thickness_m', 0):.2f} м",
        ))
        pos += 1

    # 8. Утепление (если требуется)
    if climate_result and climate_result.get("insulation_required"):
        thickness = climate_result.get("insulation_thickness_mm", 0)
        items.append(BOMItem(
            section="insulation",
            position_no=pos,
            name=f"Утепление трубопровода минвата {thickness} мм",
            quantity=climate_result.get("pipe_length_m", 50),
            units="м",
            price_rub_2026=350,  # ориентировочно за пог.м
        ))
        pos += 1

    return BOMSpecification(
        project_code=project_code,
        project_name=project_name,
        items=items,
    )
