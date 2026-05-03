"""Тесты прогона docling на одном PDF-чанке.

Все тесты в этом модуле — медленные (загрузка docling-моделей + конвертация
занимает 20-60 сек на CPU), помечены `@pytest.mark.slow` и по умолчанию
пропускаются (см. addopts в pyproject.toml).

Для запуска: `pytest backend -q -m slow`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pump_calculator.etl.pdf.docling_runner import DocumentChunk, run_docling
from pump_calculator.etl.pdf.splitter import split_pdf

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "pedrollo_vx_50hz.pdf"


@pytest.mark.slow
def test_run_docling_in_process(tmp_path: Path) -> None:
    """In-process прогон одного чанка → markdown непустой и содержит Q или H.

    Используем pages_per_chunk=4 чтобы получить один чанк со всеми страницами
    и в markdown гарантированно были и таблица параметров, и подписи кривых.
    """
    chunks = split_pdf(FIXTURE_PDF, tmp_path / "chunks", pages_per_chunk=4)
    assert len(chunks) == 1, "ожидаем один чанк (4 стр / 4)"

    result = run_docling(
        chunks[0],
        output_dir=tmp_path / "docling",
        ocr_lang=("en",),
        use_subprocess=False,
    )

    assert isinstance(result, DocumentChunk)
    assert result.markdown, "markdown должен быть непустым"
    # Проверяем, что хотя бы одна из физических меток присутствует
    md_upper = result.markdown.upper()
    assert "Q" in md_upper or "H" in md_upper, (
        "ожидаем встретить Q или H в markdown — это паспорт насоса"
    )
    assert result.page_start == 1
    assert result.page_end == 4
    assert result.runtime_sec > 0


@pytest.mark.slow
def test_run_docling_subprocess_creates_artifacts(tmp_path: Path) -> None:
    """Subprocess-режим: проверяем что worker создал три файла chunk_0.{json,md,tables.json}."""
    chunks = split_pdf(FIXTURE_PDF, tmp_path / "chunks", pages_per_chunk=2)
    assert len(chunks) >= 1

    docling_dir = tmp_path / "docling"
    result = run_docling(
        chunks[0],
        output_dir=docling_dir,
        ocr_lang=("en",),
        use_subprocess=True,
    )

    json_path = docling_dir / "chunk_0.json"
    md_path = docling_dir / "chunk_0.md"
    tables_path = docling_dir / "chunk_0.tables.json"

    assert json_path.exists(), f"missing: {json_path}"
    assert md_path.exists(), f"missing: {md_path}"
    assert tables_path.exists(), f"missing: {tables_path}"

    assert result.markdown == md_path.read_text(encoding="utf-8")
    assert isinstance(result.tables, list)
    assert result.raw_json_path == json_path
