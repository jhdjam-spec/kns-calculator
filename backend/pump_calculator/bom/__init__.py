"""Phase 30: Расширенный BOM (спецификация с артикулами).

Объединяет результаты:
- matching → насос
- corpus_sizing → корпус
- electrical/control_panel → шкаф
- physics_advanced → обвязка по фитингам
- los → ЛОС-блок (если требуется)
- climate → утепление
- structural → пригруз бетоном

Каждая позиция: name, article, manufacturer, quantity, units,
price_rub_2026, lead_time_days, supplier, source_url.

Может экспортироваться в CSV/Excel для интеграции с ГРАНД-Сметой.
"""
from .builder import (
    BOMItem,
    BOMSpecification,
    build_full_bom,
)
from .export import (
    export_bom_csv,
    export_bom_markdown,
)

__all__ = [
    "BOMItem",
    "BOMSpecification",
    "build_full_bom",
    "export_bom_csv",
    "export_bom_markdown",
]
