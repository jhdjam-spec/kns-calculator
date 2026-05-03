# ETL Guide — PDF-каталоги в pumps.json

> Phase 6 пайплайн: PDF-каталог производителя → набор `RawPumpRecord` → `pumps.json`.
> Поддержка: Pedrollo VX (production), KSB / KAIQUAN / Antarus / Wilo (тестировано частично).

## TL;DR

```bash
# 1. Установка зависимостей (один раз)
cd backend
pip install -e ".[dev,pdf]"

# 2. Прогон каталога → run-dir с артефактами
python -m pump_calculator.etl.cli parse \
    tests/fixtures/pedrollo_vx_50hz.pdf \
    --brand Pedrollo

# stdout: путь к runs/<timestamp>-<hash>
# stderr: статистика (Validated/Quarantine/Errors/Runtime)

# 3. Просмотр diff-отчёта
python -m pump_calculator.etl.cli review runs/<latest>

# 4. Merge в pumps.json (только новые)
python -m pump_calculator.etl.cli merge runs/<latest>

# 5. Merge с перезаписью существующих
python -m pump_calculator.etl.cli merge runs/<latest> --overwrite
```

## Установка

### Системные требования
- **Python ≥ 3.11** (тестировано 3.11, 3.12, 3.14)
- **Windows / Linux / macOS** (CI прогоняет на Ubuntu)
- ~2 ГБ свободной RAM (при docling — больше)

### Опциональные системные пакеты для OCR
Нужны только если используешь `--runner docling` на сканах:
```bash
# Linux (Debian/Ubuntu):
sudo apt install tesseract-ocr tesseract-ocr-rus

# Windows:
choco install tesseract
# затем скачать tessdata/rus.traineddata в C:\Program Files\Tesseract-OCR\tessdata\
```

### Python-окружение
```bash
cd backend
pip install -e ".[dev,pdf]"
```

`pdf` extras добавляет: `docling`, `pypdf`, `pdfplumber`, `easyocr`,
`plotdigitizer`, `pillow`, `pydantic-ai`, `structlog`, `pdf2image`.

### Опционально: ANTHROPIC_API_KEY

Нужен только для `table_extractor(use_llm=True)` — LLM-режим извлечения
таблиц для каталогов со сложной разметкой (когда rule-based не справляется).
По умолчанию использует rule-based, ключ не нужен.

```powershell
# PowerShell (Windows)
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# bash (Linux/macOS)
export ANTHROPIC_API_KEY=sk-ant-...
```

## Команды CLI

### `parse <pdf> --brand X`
Прогон ETL pipeline на одном PDF.

| Флаг | По умолчанию | Описание |
|---|---|---|
| `--brand` | (обязательный) | Бренд: Pedrollo / Wilo / KSB / KAIQUAN / Antarus / ... |
| `--runner` | `pdfplumber` | `pdfplumber` (vector text) или `docling` (сканы / OCR) |
| `--pages-per-chunk` | `4` | Размер чанка для splitter (можно увеличить для коротких datasheet) |
| `--runs-root` | `backend/runs/` | Куда писать прогон |

**Возвращает:** в stdout — путь к `runs/<id>/`. Exit код:
- `0` — успех (могут быть quarantine, но pipeline отработал)
- `2` — были errors на runner-этапе

### `review <run_dir>`
Печатает `runs/<id>/07_diff.md` в stdout.

Diff показывает:
- **Новые модели** (будут добавлены при merge)
- **Совпадения по id** (skip или overwrite)
- **Уже в БД, не появились в прогоне** (информативно)

### `merge <run_dir> [--overwrite] [--target path]`
Сливает `05_validated.json` прогона в `02_dataset/pumps/pumps.json`.

| Флаг | По умолчанию | Описание |
|---|---|---|
| `--overwrite` | false | Перезаписывать существующие id (по умолчанию — пропускать) |
| `--target` | `02_dataset/pumps/pumps.json` | Альтернативный pumps.json (полезно для тестов) |

Под капотом:
1. Читает `05_validated.json` (list[RawPumpRecord-dict])
2. Прогоняет через `importer.import_raw_pump` (parabolic Q-H fit + envelope)
3. Сливает с `pumps.json` через `merge_into_pumps_json`

Все импортированные записи получают `_engineer_flag=needs_review` —
инженер должен пройтись по ним перед production-использованием.

### `import <json>` (Phase 5, существующий)
Прямой импорт `RawPumpRecord[]` из заранее заготовленного JSON. Используется для
ручного ввода и unit-тестов. Полные параметры — `cli.py --help`.

## Артефакты прогона

Каждый прогон создаёт `runs/<timestamp>-<hash>/`:

```
runs/20260503-181500-abc123/
├── input.pdf              копия исходника (для traceability)
├── meta.json              {pdf_sha256, brand, runner, started_at, ...}
├── 01_chunks/             вырезанные PDF-чанки
│   └── chunk_0_pp_1-4.pdf
├── 02_extract/            вывод runner'а
│   ├── chunk_0.md         markdown (text + tables)
│   └── chunk_0.tables.json  список таблиц
├── 03_drafts.json         RawPumpDraft[] (без qh_curve)
├── 04_curves.json         dict[model, list[QHPoint]]
├── 05_validated.json      ⭐ list[RawPumpRecord-dict] для merge
├── 06_quarantine.json     draft'ы, не прошедшие Pydantic-валидацию
└── 07_diff.md             markdown diff vs существующий pumps.json
```

`runs/` находится в `.gitignore` — артефакты не коммитятся, только финальный
`05_validated.json` можно сохранить в `02_dataset/etl_seed/<brand>_<series>.json`
для воспроизводимости (см. `02_dataset/etl_seed/pedrollo_vx_50hz.json`).

## Pipeline detail

### Этап 1: Splitter (`splitter.py`)
`pypdf` режет PDF на чанки по `--pages-per-chunk`. Чанки кладутся в
`01_chunks/chunk_<idx>_pp_<start>-<end>.pdf`.

### Этап 2: Runner
**`pdfplumber_runner.py`** (default) — извлекает текст и таблицы из vector-text
PDF (Pedrollo, Wilo, KSB Amarex KRT). Не делает OCR. Быстрый, идеален для CI.

**`docling_runner.py` + `_docling_worker.py`** — для сканов и плохо извлекаемых
PDF (KAIQUAN). Обёртка вокруг `docling 2.92` через `subprocess.run([sys.executable,
"-m", "..._docling_worker", ...])` — обязательно из-за memory leak (docling#2209,
#2829). На Windows+Python 3.14 docling может падать с `std::bad_alloc` —
используй `pdfplumber` как primary.

Оба возвращают одинаковый `DocumentChunk(markdown, tables, ...)`.

### Этап 3: Table extractor (`table_extractor.py`)
Rule-based парсер ищет:
- **Anchor-таблицы** (regex `V[Xx]m? \d+/\d+` — паттерн модели Pedrollo;
  для других брендов — настроить regex в модуле)
- **PORT/Passage таблицу** (DN и `free_passage_mm`)
- **Power column** (P2 kW)

Сшивает в `RawPumpDraft[]` (Pydantic-модель без обязательной `qh_curve`).
Для Pedrollo VX даёт 16 моделей (8 single-phase VXm + 8 three-phase VX).

LLM-режим (`use_llm=True`, требует `ANTHROPIC_API_KEY`): Pydantic-AI Agent на
`claude-haiku-4-5-20251001` с retry-on-validation. Используется для каталогов
со сложной разметкой.

### Этап 4: Q-H extractor (`qh_extractor.py`)
Для **табличных Q-H матриц** (Pedrollo, многие dwell pumps).

Алгоритм:
1. Найти таблицу с числовым заголовком (Q-значения вдоль оси) и строками
   моделей в первой колонке
2. Извлечь Q-значения справа от метки `³/h` (м³/ч предпочтительно) или
   `min` (л/мин с конвертацией ×0.06)
3. Для каждой строки модели — H-числа справа от `H metres` (отсекает P_kW
   колонки)
4. Вернуть `dict[model_name, list[QHPoint]]`

Для **графических Q-H** (KSB / KAIQUAN, без числовых таблиц) — модуль
`curve_digitizer.py` (STUB до Phase 6.6, реализация на PlotDigitizer
+ color masking).

### Этап 5: Сшивка + Pydantic-валидация
`pipeline.py::parse_catalog`:
- Для каждого `RawPumpDraft` — берёт `qh_points = curves.get(draft.model, [])`
- Собирает dict в формате `RawPumpRecord` (см. `etl/schemas.py`)
- Валидирует через `RawPumpRecord.model_validate()`:
  - валидные → `validated[]` → `05_validated.json`
  - упавшие (нет qh_curve, ошибка типов и т.п.) → `quarantine[]` → `06_quarantine.json`

### Этап 6: Diff (`review.py`)
`build_diff_report(validated, brand)` → markdown:
- Новые модели (по generated id из `_make_pump_id(brand, model)`)
- Совпадения с существующими (нужен `--overwrite` для замены)
- Существующие, не появившиеся в прогоне (информативно)

### Этап 7: Merge (CLI command)
`importer.import_raw_pump` делает parabolic fit Q-H через `curve_fitter`,
собирает envelope (`Q_min/max`, `H_min/max`, `Q_BEP`, `eta_BEP`).
`merge_into_pumps_json` сливает в `02_dataset/pumps/pumps.json`.

## Добавление нового бренда

1. **Найти PDF-каталог** (см. `00_research/PHASE6_RESEARCH.md` § Test fixtures)
2. **Скачать в `backend/tests/fixtures/<brand>_<series>.pdf`** (если открыто
   распространяемый — можно коммитить; иначе добавить в `.gitignore` и хранить
   локально)
3. **Прогнать `cli parse <pdf> --brand <Brand>`** — проверить что
   `05_validated.json` непустой и `07_diff.md` показывает разумные модели
4. **Если rule-based не справляется** (модели не находятся, поля не
   собираются):
   - Доработать regex `MODEL_NAME_RE` в `table_extractor.py` для нового
     паттерна именования бренда
   - Доработать `_extract_q_values` в `qh_extractor.py` для специфики
     заголовка таблицы
   - Альтернативно — попробовать `--runner docling` с OCR
   - Last resort — `extract_pumps_from_chunks(use_llm=True)`
5. **Написать unit-тесты** в `backend/tests/test_etl_pdf_<brand>.py` (3-5
   проверок: число моделей, brand, P_kW для одного экземпляра, free_passage,
   shutoff head)
6. **Прогнать `cli merge`** в pumps.json и проверить, что
   `test_matching_myshako` остаётся зелёным (regression)
7. **Обновить `02_dataset/pumps/producers.json`** с
   `etl_status: {covered_by_etl_v1: true, models_imported: N, ...}`

## Поддерживаемые бренды (на 2026-05)

| Бренд | Статус | PDF-источник | Модели |
|---|---|---|---|
| **Pedrollo** | ✅ ETL v1 | [VX 50Hz datasheet](https://www.pedrollo.com/wp-content/uploads/schede-tecniche/EN/VX_EN-datasheet_50Hz.pdf) | 16 (VXm + VX серий /35 и /50) |
| KAIQUAN | ⚠️ ETL stub | [WQ catalog 40 МБ](https://www.kqpump.com/uploads/Catalog--WQ%20Submersible%20Sewage%20Pump.pdf) | 6 manual; ETL Phase 6.6 |
| Wilo | ⚠️ ETL stub | [Rexa catalog](https://cms.media.wilo.com/cdndoc/wilo249379/6929984/wilo249379.pdf) | 4 manual |
| KSB | ⚠️ ETL stub | [Amarex KRT](https://www.lenntech.com/Data-sheets/KSB-AmaRex-KRT-50-Hz-EN-L.pdf) | 2 manual |
| Antarus | ⚠️ ETL stub | [НК manual ru](https://www.c-o-k.ru/library/instructions/antarus/kanalizacionnye-nasosy/35874/131021.pdf) | 4 manual; Cyrillic CID/WinAnsi баг |
| Grundfos | ⚠️ manual | parallel import 2026 | 2 manual |
| LEO | ⚠️ manual | brochure только | 1 manual |
| Aquario/Belamos/Unipump | — | HTML-карточки | — |

## Troubleshooting

**docling падает с `std::bad_alloc`** (Windows + Python 3.14):
→ Используй `--runner pdfplumber`. Это известная проблема pdfium image rendering.

**`No DocumentChunks were produced`**:
→ PDF испорчен или нечитаем. Проверь `pypdf.PdfReader(pdf).pages`.

**Quarantine > 0 при Pedrollo VX**:
→ Скорее всего регресс в `qh_extractor` — посмотреть `06_quarantine.json[].error`.
Каждая запись содержит исходный draft и сообщение Pydantic.

**`free_passage_mm` валидно, но из «магического» fallback**:
→ DN/Passage таблица не нашлась. Проверь регекс `_is_dn_passage_table` в
`table_extractor.py`.

**ANTHROPIC_API_KEY missing при `use_llm=True`**:
→ Установи env var или используй `use_llm=False` (по умолчанию).
