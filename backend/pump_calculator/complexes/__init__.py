"""Phase 29: Многообъектные комплексы (РЭУ → площадка → объект).

Эталон — КС-14 КазТрансГаз, шифр 926228, 5 площадок, 43 ОЛ
(см. reference_kns_kc14_kaztransgas_kazakhstan).

Структура:
- Complex (комплекс) — РЭУ или промплощадка с несколькими объектами
- Site (площадка) — отдельная площадка в составе комплекса
- ObjectKNS (объект) — конкретная КНС/ВНС/ЛОС на площадке

Сводная BOM объединяет все объекты комплекса.
"""
from .models import (
    Complex,
    ComplexBOMSummary,
    ComplexInput,
    ObjectInComplex,
    Site,
)
from .summary import build_complex_bom_summary

__all__ = [
    "Complex",
    "ComplexBOMSummary",
    "ComplexInput",
    "ObjectInComplex",
    "Site",
    "build_complex_bom_summary",
]
