"""Phase 6 — PDF→RawPumpRecord pipeline.

Modules:
    splitter         — pypdf разрез PDF на страницы/чанки
    docling_runner   — subprocess wrapper для docling (memory-safe)
    table_extractor  — Pydantic-AI агент: markdown-таблица → RawPumpDraft[]
    curve_digitizer  — PlotDigitizer batch + color masking для multi-curve graphs
"""
