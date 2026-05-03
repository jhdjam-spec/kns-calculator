"""Phase 4 — Hand-off PDF generators.

Соответствует спецификации 01_spec/handoff.md (3 артефакта):
1. PDF опросный лист клиенту  — `questionnaire_pdf.py`
2. BOM-черновик               — `bom_pdf.py`
3. JSON-payload для CRM       — генерируется в api.py из SelectionResult напрямую
"""

from pump_calculator.handoff.questionnaire_pdf import generate_questionnaire_pdf
from pump_calculator.handoff.bom_pdf import generate_bom_pdf

__all__ = ["generate_questionnaire_pdf", "generate_bom_pdf"]
