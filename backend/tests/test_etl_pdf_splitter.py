"""Тесты сплиттера PDF (`pump_calculator.etl.pdf.splitter`).

Все тесты — быстрые (без docling), используют тест-фикстуру
`fixtures/pedrollo_vx_50hz.pdf` (4 страницы, 1.5 МБ).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from pump_calculator.etl.pdf.splitter import ChunkSpec, split_pdf

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "pedrollo_vx_50hz.pdf"


def test_split_pedrollo_vx_returns_2_chunks(tmp_path: Path) -> None:
    """4 страницы / 2 страницы на чанк → ровно 2 чанка."""
    chunks = split_pdf(FIXTURE_PDF, tmp_path, pages_per_chunk=2)

    assert len(chunks) == 2
    assert all(isinstance(c, ChunkSpec) for c in chunks)
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 2
    assert chunks[1].page_start == 3
    assert chunks[1].page_end == 4


def test_split_pdf_creates_output_files(tmp_path: Path) -> None:
    """Все output_pdf файлы существуют, читаемы pypdf и содержат правильное число страниц."""
    chunks = split_pdf(FIXTURE_PDF, tmp_path, pages_per_chunk=2)

    for chunk in chunks:
        assert chunk.output_pdf.exists(), f"Missing chunk file: {chunk.output_pdf}"
        assert chunk.output_pdf.suffix == ".pdf"
        reader = PdfReader(str(chunk.output_pdf))
        expected_pages = chunk.page_end - chunk.page_start + 1
        assert len(reader.pages) == expected_pages, (
            f"chunk {chunk.chunk_index}: expected {expected_pages} pages, "
            f"got {len(reader.pages)}"
        )


def test_split_pdf_short_returns_one_chunk(tmp_path: Path) -> None:
    """PDF из одной страницы → один чанк со всеми страницами."""
    # Готовим однастраничный PDF на лету
    one_page = tmp_path / "one_page.pdf"
    reader = PdfReader(str(FIXTURE_PDF))
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    with open(one_page, "wb") as fh:
        writer.write(fh)

    chunks = split_pdf(one_page, tmp_path / "out", pages_per_chunk=4)

    assert len(chunks) == 1
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
    assert chunks[0].output_pdf.exists()
    assert len(PdfReader(str(chunks[0].output_pdf)).pages) == 1


def test_split_pdf_uneven_chunks(tmp_path: Path) -> None:
    """4 страницы / 3 страницы на чанк → 2 чанка (3 + 1)."""
    chunks = split_pdf(FIXTURE_PDF, tmp_path, pages_per_chunk=3)

    assert len(chunks) == 2
    assert chunks[0].page_start == 1 and chunks[0].page_end == 3
    assert chunks[1].page_start == 4 and chunks[1].page_end == 4


def test_split_pdf_invalid_pages_per_chunk(tmp_path: Path) -> None:
    """pages_per_chunk < 1 → ValueError."""
    with pytest.raises(ValueError, match="pages_per_chunk"):
        split_pdf(FIXTURE_PDF, tmp_path, pages_per_chunk=0)


def test_split_pdf_missing_file(tmp_path: Path) -> None:
    """Несуществующий PDF → FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        split_pdf(tmp_path / "nope.pdf", tmp_path)
