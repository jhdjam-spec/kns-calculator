"""Тесты pdfplumber-runner для vector-text PDF.

Эти тесты быстрые (без docling-моделей), пригодны для CI и default-прогона.
Pedrollo VX — vector text Adobe InDesign, идеально извлекается pdfplumber.
"""

from __future__ import annotations

from pathlib import Path

from pump_calculator.etl.pdf.pdfplumber_runner import run_pdfplumber
from pump_calculator.etl.pdf.splitter import split_pdf

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "pedrollo_vx_50hz.pdf"


def test_pdfplumber_runner_extracts_pedrollo_markdown(tmp_path: Path) -> None:
    """На странице 2 Pedrollo VX должны быть видны Q-H заголовки и хоть одна модель."""
    chunks = split_pdf(FIXTURE_PDF, tmp_path / "chunks", pages_per_chunk=4)
    assert len(chunks) == 1

    result = run_pdfplumber(chunks[0], output_dir=tmp_path / "plumber")

    md = result.markdown
    assert md, "markdown пустой"
    # Pedrollo VX содержит модели типа "VXm 8/35", "VX 8/35"
    assert "VX" in md
    # Q (расход) и H (напор) — обязательные физические метки на стр 2
    assert "Q" in md
    assert "H" in md
    # Один из конкретных типоразмеров должен быть в тексте
    assert "8/35" in md or "10/35" in md or "15/50" in md


def test_pdfplumber_runner_extracts_tables(tmp_path: Path) -> None:
    """pdfplumber должен извлечь несколько таблиц (Pedrollo VX = ~6+ таблиц на 4 страницах)."""
    chunks = split_pdf(FIXTURE_PDF, tmp_path / "chunks", pages_per_chunk=4)
    result = run_pdfplumber(chunks[0], output_dir=tmp_path / "plumber")

    assert isinstance(result.tables, list)
    assert len(result.tables) >= 3, (
        f"ожидаем минимум 3 таблицы в Pedrollo VX, получили {len(result.tables)}"
    )
    for tbl in result.tables:
        assert "page_no" in tbl
        assert "df" in tbl
        assert "header" in tbl
        assert tbl["page_no"] in {1, 2, 3, 4}


def test_pdfplumber_runner_creates_artifacts(tmp_path: Path) -> None:
    """chunk_{idx}.md и chunk_{idx}.tables.json должны существовать после прогона."""
    chunks = split_pdf(FIXTURE_PDF, tmp_path / "chunks", pages_per_chunk=2)
    plumber_dir = tmp_path / "plumber"

    result = run_pdfplumber(chunks[0], output_dir=plumber_dir)

    md_path = plumber_dir / "chunk_0.md"
    tables_path = plumber_dir / "chunk_0.tables.json"

    assert md_path.exists()
    assert tables_path.exists()
    assert result.markdown == md_path.read_text(encoding="utf-8")
    # raw_json_path не пишется pdfplumber-runner'ом
    assert result.raw_json_path is None
    assert result.runtime_sec > 0
