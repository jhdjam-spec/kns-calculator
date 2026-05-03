"""Детерминированный разрез PDF-каталога на страничные чанки.

Зачем нужно: docling склонен к утечкам памяти при батчевой обработке (issues
docling#2209, docling#2829). Мы режем большие каталоги на небольшие чанки
(2-3 страницы) и обрабатываем каждый в отдельном subprocess (см.
`docling_runner`). Сплиттер — детерминированный, без сторонних эффектов кроме
записи нарезанных PDF-ов на диск.

Контракт:
    >>> chunks = split_pdf("catalog.pdf", "out/", pages_per_chunk=2)
    >>> chunks[0]
    ChunkSpec(source_pdf=..., chunk_index=0, page_start=1, page_end=2,
              output_pdf=Path('out/chunk_0_pp_1-2.pdf'))
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter


@dataclass(frozen=True)
class ChunkSpec:
    """Один чанк страниц для последующей обработки docling.

    Атрибуты:
        source_pdf:  абсолютный путь к исходному (полному) PDF
        chunk_index: 0-based индекс чанка в порядке появления
        page_start:  1-based номер первой страницы чанка (включительно)
        page_end:    1-based номер последней страницы чанка (включительно)
        output_pdf:  путь к вырезанному PDF этого чанка
    """

    source_pdf: Path
    chunk_index: int
    page_start: int
    page_end: int
    output_pdf: Path


def split_pdf(
    pdf_path: Path | str,
    output_dir: Path | str,
    pages_per_chunk: int = 2,
) -> list[ChunkSpec]:
    """Разрезать PDF на чанки по `pages_per_chunk` страниц.

    Использует pypdf. Создаёт `output_dir/chunk_<idx>_pp_<start>-<end>.pdf`
    для каждого чанка.

    Args:
        pdf_path: путь к исходному PDF (любой — относительный или абсолютный)
        output_dir: директория для вырезанных PDF; создаётся при необходимости
        pages_per_chunk: число страниц в одном чанке (>=1)

    Returns:
        Упорядоченный список ChunkSpec (по возрастанию chunk_index).

    Особенности:
        - Если PDF короче `pages_per_chunk` — один чанк со всеми страницами.
        - Если total_pages не делится нацело — последний чанк короче.
        - source_pdf и output_pdf резолвятся в абсолютные пути для
          предсказуемого поведения subprocess'ов.

    Raises:
        ValueError: если pages_per_chunk < 1 или PDF не содержит страниц.
        FileNotFoundError: если pdf_path не существует.
    """
    if pages_per_chunk < 1:
        raise ValueError(f"pages_per_chunk must be >= 1, got {pages_per_chunk}")

    source = Path(pdf_path).resolve()
    if not source.exists():
        raise FileNotFoundError(f"PDF not found: {source}")

    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(source))
    total_pages = len(reader.pages)
    if total_pages == 0:
        raise ValueError(f"PDF has no pages: {source}")

    chunks: list[ChunkSpec] = []
    chunk_index = 0
    # 0-based страничный курсор; в ChunkSpec выводим 1-based для удобства человека.
    for start_idx in range(0, total_pages, pages_per_chunk):
        end_idx = min(start_idx + pages_per_chunk, total_pages)  # exclusive
        page_start = start_idx + 1
        page_end = end_idx  # уже 1-based включительно
        output_pdf = out_dir / f"chunk_{chunk_index}_pp_{page_start}-{page_end}.pdf"

        writer = PdfWriter()
        for page_idx in range(start_idx, end_idx):
            writer.add_page(reader.pages[page_idx])
        with open(output_pdf, "wb") as fh:
            writer.write(fh)

        chunks.append(
            ChunkSpec(
                source_pdf=source,
                chunk_index=chunk_index,
                page_start=page_start,
                page_end=page_end,
                output_pdf=output_pdf,
            )
        )
        chunk_index += 1

    return chunks
