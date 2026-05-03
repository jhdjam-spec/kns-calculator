"""Альтернативный runner для vector-text PDF через pdfplumber.

Зачем нужно: docling 2.92 на Windows+Python 3.14 падает с std::bad_alloc
при загрузке pdfium image-rendering моделей даже на простых vector PDF.
pdfplumber работает на чистом Python и идеально подходит для vector-text
каталогов (Pedrollo VX, Wilo, KSB Amarex KRT — у них embedded шрифты).

Возвращает тот же `DocumentChunk` контракт что и `docling_runner.run_docling`,
поэтому `pipeline.py` (этап 6.4) может выбирать runner по флагу/евристике.

Ограничения:
    - Не делает OCR (для сканированных PDF — недостаточен).
    - Markdown сборки таблиц — простая (pipe-separated rows).
    - Работает только с vector-extractable text.

Для сканированных и плохо извлекаемых PDF (KAIQUAN, ANTARUS) — оставляем
docling_runner, который имеет OCR-pipeline (см. docs/ETL_GUIDE.md).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pdfplumber

from pump_calculator.etl.pdf.docling_runner import DocumentChunk
from pump_calculator.etl.pdf.splitter import ChunkSpec


def _table_to_md(rows: list[list[str | None]]) -> str:
    """Конвертировать таблицу pdfplumber в простой markdown."""
    if not rows:
        return ""
    cleaned = [[("" if c is None else str(c).strip()) for c in row] for row in rows]
    header = cleaned[0]
    lines = ["| " + " | ".join(header) + " |"]
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in cleaned[1:]:
        # Выровнять длину строки до длины заголовка
        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))
        elif len(row) > len(header):
            row = row[: len(header)]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def run_pdfplumber(
    chunk_spec: ChunkSpec,
    output_dir: Path | str,
) -> DocumentChunk:
    """Извлечь текст и таблицы из PDF-чанка через pdfplumber.

    Артефакты:
        {output_dir}/chunk_{idx}.md           markdown (text + tables)
        {output_dir}/chunk_{idx}.tables.json  список таблиц (тот же формат что у docling worker)

    JSON «raw export» здесь не пишем — pdfplumber не имеет богатого AST,
    только страницы и таблицы. Поле raw_json_path остаётся None.

    Args:
        chunk_spec: результат `splitter.split_pdf` для одного чанка.
        output_dir: директория для артефактов.

    Returns:
        DocumentChunk с заполненным markdown и tables.
    """
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()

    md_parts: list[str] = []
    tables_out: list[dict] = []

    with pdfplumber.open(str(chunk_spec.output_pdf)) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            # Абсолютный номер страницы в исходном PDF
            absolute_page_no = chunk_spec.page_start + page_idx - 1

            md_parts.append(f"\n## Page {absolute_page_no}\n")

            # Текст
            text = page.extract_text() or ""
            if text.strip():
                md_parts.append(text)

            # Таблицы
            page_tables = page.extract_tables() or []
            for tbl_idx, rows in enumerate(page_tables):
                if not rows:
                    continue
                header = [
                    ("" if c is None else str(c).strip()) for c in rows[0]
                ]
                df_rows = [
                    [("" if c is None else str(c).strip()) for c in row]
                    for row in rows[1:]
                ]
                tables_out.append(
                    {
                        "page_no": absolute_page_no,
                        "df": df_rows,
                        "header": header,
                    }
                )
                md_parts.append(f"\n### Table p.{absolute_page_no}-{tbl_idx}\n")
                md_parts.append(_table_to_md(rows))

    markdown = "\n".join(md_parts).strip() + "\n"

    md_path = out_dir / f"chunk_{chunk_spec.chunk_index}.md"
    md_path.write_text(markdown, encoding="utf-8")

    tables_path = out_dir / f"chunk_{chunk_spec.chunk_index}.tables.json"
    tables_path.write_text(
        json.dumps(tables_out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    runtime = time.perf_counter() - started

    return DocumentChunk(
        source_pdf=chunk_spec.source_pdf,
        chunk_pdf=chunk_spec.output_pdf,
        page_start=chunk_spec.page_start,
        page_end=chunk_spec.page_end,
        markdown=markdown,
        tables=tables_out,
        raw_json_path=None,
        runtime_sec=runtime,
    )
