"""Phase 4 — Hand-off PDF/DOCX generators + DOCX-парсер для возврата.

Соответствует спецификации 01_spec/handoff.md:
1. PDF опросный лист клиенту  — `questionnaire_pdf.py` (для печати)
2. DOCX опросный лист клиенту — `questionnaire_docx.py` (для редактирования и парсинга)
3. BOM-черновик               — `bom_pdf.py`
4. Парсер заполненного DOCX   — `quiz_extractor.py` (Phase 12 — приём опросника обратно)
"""

from pump_calculator.handoff.bom_pdf import generate_bom_pdf
from pump_calculator.handoff.questionnaire_docx import generate_questionnaire_docx
from pump_calculator.handoff.questionnaire_pdf import generate_questionnaire_pdf
from pump_calculator.handoff.quiz_extractor import ExtractedQuiz, parse_questionnaire_docx

__all__ = [
    "ExtractedQuiz",
    "generate_bom_pdf",
    "generate_questionnaire_docx",
    "generate_questionnaire_pdf",
    "parse_questionnaire_docx",
]
