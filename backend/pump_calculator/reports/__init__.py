"""Phase 28: Генерация инженерной расчётной записки.

Источники для шаблона:
- reference_kns_calculation_template_docx — образец на 2 КНС из реальной сделки
- INSERVO Studio brand-line (Layer 2 ADR-002)

Структура отчёта (5 секций):
1. Опросный лист (входные данные)
2. Методика расчёта (формулы, нормативы)
3. Результаты расчёта (Q-H, NPSH, мощность, шкаф, корпус)
4. Спецификация (BOM с артикулами)
5. Выводы и рекомендации
"""
from .calculation_report import (
    CalculationReportInput,
    generate_calculation_report_pdf,
)

__all__ = [
    "CalculationReportInput",
    "generate_calculation_report_pdf",
]
