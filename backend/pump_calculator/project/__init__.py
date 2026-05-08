"""Phase 32: Единый «Проект» — главный flow калькулятора.

Объединяет все расчётные модули (Phase 22-30) в одну сборку:
пользователь вводит параметры объекта раз → получает все расчёты + BOM + PDF.

Эталоны проекта (presets):
- ИЖС / коттедж (4-5 чел)
- Многоквартирный ЖК (50-200 квартир)
- АЗС / автомойка
- Гостиница / отель
- ТРЦ / БЦ
- Промпредприятие
- Газпром-объект (СТО)
"""
from .models import (
    ProjectInput,
    ProjectPreset,
    ProjectResult,
    ProjectSubsystems,
)
from .orchestrator import calculate_project, list_presets

__all__ = [
    "ProjectInput",
    "ProjectPreset",
    "ProjectResult",
    "ProjectSubsystems",
    "calculate_project",
    "list_presets",
]
