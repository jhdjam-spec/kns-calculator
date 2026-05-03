# Phase 6 — Research Snapshot

> **Дата:** 2026-05-03
> **Цель:** зафиксировать выводы 4 параллельных research-захода для traceability при разработке Phase 6 ETL (PDF→pumps.json).
> **Решения по развилкам зафиксированы пользователем:** см. `plans/wiggly-riding-candy.md` Context.

## 1. PDF parsers (2026)

**Главный выбор: docling 2.92** (IBM/MIT, ~58.6k★).
- 97.9% точности на сложных таблицах sustainability-отчётов; **слаб** на dense pump-каталогах со многими типоразмерами в одной таблице — нужен post-processing (regex split / валидация по числу столбцов).
- Производительность: 0.79 сек/стр median CPU; 200-стр каталог ~1 час без GPU.
- **Critical**: memory leak (issue #2209, #2829) — обязательный паттерн **subprocess-per-PDF**, иначе на batch память растёт с 500 МБ до 13.7 ГБ.
- Кириллица: через EasyOCR (`lang=["ru","en"]`) или Tesseract (`tesseract-ocr-rus`).

**Backup: Marker (datalab-to/marker, MIT)** — на olmOCR-Bench бьёт GPT-4o, DeepSeek OCR, Mistral OCR. Подключаем как cross-validator на стабилизации.

**Отклонены для Phase 6:**
- Unstructured / LlamaParse / Adobe Extract — cloud, $$$
- Nougat (Meta) — устарел, заточен под arXiv
- camelot — 5 лет без коммитов
- pdfplumber — оставляем как fallback на vector-text PDF (Pedrollo VX)

## 2. Q-H curve digitization

**Главный выбор: dilawar/PlotDigitizer v0.3.0** (GPL-3.0, июль 2024).
- CLI batch есть, но **только grayscale** и **только одна траектория** на изображение.
- Калибровка: `-p 0,0 -p 20,0 -p 0,1` (data) + `-l 22,295 -l 142,295` (pixels).
- Для каталогов с 5-10 кривыми Q-H разных диаметров на одном графике — **резать изображение по цветам через PIL color masking** перед подачей в PlotDigitizer.

**WebPlotDigitizer 5.2** (Ankit Rohatgi) — GUI; batch только через JS-плагины. AI-автоматизация анонсирована, но релиза нет.

**Альтернатива (не выбрана пользователем):** Claude Sonnet 4.6 Vision — лучшая VLM-точка точек на CHART2CSV (~$0.012 за кривую с prompt caching). Отложено до Phase 6.5 как fallback на multi-curve color graphs.

## 3. Multi-agent orchestration

**Главный выбор: Pydantic-AI + asyncio** (MIT, минимум зависимостей).
- Strict-typed агенты с `result_type=list[RawPumpDraft]`, retry-on-validation встроен.
- Прямой `anthropic` SDK для запросов, `asyncio.gather` для concurrent extract.
- Без графов — наш pipeline линейный, графовая топология (LangGraph) избыточна.

**Отклонены:**
- LangGraph 1.x — мощно, но overkill для линейного PDF→JSON. Перейти, если появятся ветвления/циклы.
- CrewAI — для role-based творческих задач, не для строгого ETL.
- AutoGen 0.4 — Microsoft перешли на Agent Framework, **maintenance mode** — избегать.
- Claude Agent SDK — лучше для autonomy-задач, не для DAG.

## 4. Test fixtures

**Стартовая фикстура: Pedrollo VX 50Hz datasheet** (https://www.pedrollo.com/wp-content/uploads/schede-tecniche/EN/VX_EN-datasheet_50Hz.pdf, 1.5 МБ, 4 стр).
- Vector text (Adobe InDesign 18.5) — `pdfplumber` справится без OCR.
- 8 моделей в одной таблице + 8 Q-H кривых на одном графике — отличный stress-test для curve digitizer.
- Содержит: model, Q (l/min + m³/h), H (m), P (kW), n (rpm), DN, weight.

**Эскалация (НЕ в Phase 6):**
- KSB Amarex KRT (~150 стр, vector text, multi-section) — proof масштабирования.
- ANTARUS НК Руководство (78 стр) — **жёсткий тест Cyrillic CID/WinAnsi mojibake** — типичная проблема российских PDF.
- KAIQUAN WQ (50+ стр, 40.8 МБ, scan-heavy) — proof для OCR-pipeline.

**Не покрыто публичным PDF:** LEO (только marketing-брошюра), Aquario/Belamos/Unipump (только HTML-карточки), Antarus (только manual).

## Стек итоговый

```toml
# backend/pyproject.toml [project.optional-dependencies] pdf
pdf = [
    "pypdf>=4.0",                # детерминированный splitter
    "pdfplumber>=0.11",          # backup table extraction для vector PDF
    "docling>=2.92",             # primary PDF parser (subprocess-per-PDF!)
    "easyocr>=1.7",              # OCR ru/en
    "plotdigitizer>=0.3",        # CLI batch curve extraction
    "pillow>=10.0",              # color masking для multi-curve graphs
    "pydantic-ai>=0.0.50",       # text normalization agent
    "structlog>=24.0",           # JSONL audit log
    "pdf2image>=1.17",           # PDF page → PNG для curve_digitizer
]
```

## Источники

См. артефакты sub-agent выжимок в conversation log от 2026-05-03 (research subagents `a23cdd0acc009f809`, `ab0c88de9e24df090`, `a5f58ad4bb3a064ab`).

Ключевые URL:
- https://github.com/docling-project/docling (issues #2209, #2829)
- https://github.com/datalab-to/marker
- https://github.com/dilawar/PlotDigitizer
- https://ai.pydantic.dev/
- https://www.pedrollo.com/wp-content/uploads/schede-tecniche/EN/VX_EN-datasheet_50Hz.pdf
- https://www.lenntech.com/Data-sheets/KSB-AmaRex-KRT-50-Hz-EN-L.pdf
- https://www.c-o-k.ru/library/instructions/antarus/kanalizacionnye-nasosy/35874/131021.pdf
