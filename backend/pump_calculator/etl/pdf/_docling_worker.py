"""Worker-модуль для прогона одного PDF-чанка через docling.

Запускается как `python -m pump_calculator.etl.pdf._docling_worker ...`
из `docling_runner.run_docling(use_subprocess=True)`. Изоляция в отдельном
процессе нужна из-за известных утечек памяти в docling
(issues docling#2209, docling#2829): после каждого PDF память
не возвращается процессу-родителю.

Контракт I/O:
    Вход — аргументы CLI:
        --chunk-pdf  путь к PDF-чанку (один или несколько страниц)
        --output-dir директория для артефактов
        --idx        chunk_index (для имён файлов, целое >=0)
        --ocr-lang   языковой код easyocr (en, ru, ...); можно повторять

    Выход — три файла в --output-dir:
        chunk_{idx}.json         raw docling DocumentStream export (pretty JSON)
        chunk_{idx}.md           markdown-экспорт (включая таблицы)
        chunk_{idx}.tables.json  список таблиц
                                 [{"page_no": int, "df": [[...]], "header": [...]}, ...]

ВАЖНО: тяжёлые импорты (docling, easyocr, torch) делаются ВНУТРИ main(),
не на уровне модуля. Это сокращает время холодного старта subprocess
для тестов и упрощает мокинг.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pump_calculator.etl.pdf._docling_worker",
        description="Прогнать один PDF-чанк через docling и сохранить артефакты.",
    )
    parser.add_argument("--chunk-pdf", required=True, help="Путь к PDF-чанку")
    parser.add_argument("--output-dir", required=True, help="Куда писать chunk_{idx}.{json,md,tables.json}")
    parser.add_argument("--idx", required=True, type=int, help="chunk_index для имён файлов")
    parser.add_argument(
        "--ocr-lang",
        action="append",
        default=None,
        help="Язык OCR (en, ru, ...); можно указать несколько раз. По умолчанию ['en'].",
    )
    return parser


def _serialize_tables(document) -> list[dict]:
    """Сериализовать таблицы документа в JSON-совместимый формат.

    Каждая таблица: {"page_no": int|None, "df": [[cell, ...], ...], "header": [...]}
    Используем `export_to_dataframe()` (если pandas доступен) или ручной обход
    `data.grid` как fallback. Если ни то, ни другое не работает — пустой список.
    """
    tables_out: list[dict] = []
    raw_tables = getattr(document, "tables", None) or []

    for tbl in raw_tables:
        # page_no: TableItem.prov[0].page_no
        page_no: int | None = None
        prov = getattr(tbl, "prov", None) or []
        if prov:
            page_no = getattr(prov[0], "page_no", None)

        df_rows: list[list[str]] = []
        header: list[str] = []

        # Try pandas-based export
        try:
            df = tbl.export_to_dataframe()
            header = [str(c) for c in df.columns.tolist()]
            df_rows = [[("" if v is None else str(v)) for v in row] for row in df.values.tolist()]
        except Exception:
            # Fallback: TableData.grid — список списков TableCell
            data = getattr(tbl, "data", None)
            grid = getattr(data, "grid", None) if data is not None else None
            if grid:
                for row in grid:
                    df_rows.append([
                        str(getattr(cell, "text", "") or "")
                        for cell in row
                    ])
                if df_rows:
                    header = df_rows[0]
                    df_rows = df_rows[1:]

        tables_out.append({"page_no": page_no, "df": df_rows, "header": header})

    return tables_out


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    chunk_pdf = Path(args.chunk_pdf).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    idx = args.idx
    ocr_lang = tuple(args.ocr_lang) if args.ocr_lang else ("en",)

    # Тяжёлые импорты — внутри main, чтобы быстрый старт subprocess
    # и чтобы тесты могли мокать модуль без падения на import.
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = PdfPipelineOptions()
    # OCR пока оставляем на дефолтных настройках docling (он сам решает,
    # нужен ли OCR на vector-text странице). Языки потребуются на следующих
    # этапах для русских каталогов — поле сохраняем в JSON для трассировки.
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )

    result = converter.convert(str(chunk_pdf))
    document = result.document

    # 1. Markdown
    markdown = document.export_to_markdown()
    md_path = output_dir / f"chunk_{idx}.md"
    md_path.write_text(markdown, encoding="utf-8")

    # 2. Tables
    tables = _serialize_tables(document)
    tables_path = output_dir / f"chunk_{idx}.tables.json"
    tables_path.write_text(
        json.dumps(tables, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 3. Raw JSON через export_to_dict (pydantic-friendly)
    json_path = output_dir / f"chunk_{idx}.json"
    try:
        raw_dict = document.export_to_dict()
    except Exception:
        # Fallback: model_dump для pydantic-моделей
        raw_dict = {
            "ocr_lang": list(ocr_lang),
            "chunk_pdf": str(chunk_pdf),
            "markdown_chars": len(markdown),
            "tables_count": len(tables),
            "fallback": True,
        }
    raw_dict.setdefault("_ocr_lang", list(ocr_lang))
    json_path.write_text(
        json.dumps(raw_dict, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # Освободить память: docling держит модели в RAM
    del result
    del document
    del converter
    gc.collect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
