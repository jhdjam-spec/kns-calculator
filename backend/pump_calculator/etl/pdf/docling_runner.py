"""Memory-safe wrapper для прогона PDF-чанков через docling.

Особенности:
    - По умолчанию (`use_subprocess=True`) docling запускается в отдельном
      Python-процессе через `python -m pump_calculator.etl.pdf._docling_worker`.
      Это нужно из-за утечек памяти на батчевой обработке (docling#2209,
      docling#2829): после возврата subprocess вся память возвращается ОС.
    - In-process режим (`use_subprocess=False`) — для unit-тестов с monkeypatch.

Артефакты worker'а:
    {output_dir}/chunk_{idx}.json         raw docling JSON (pretty)
    {output_dir}/chunk_{idx}.md           markdown
    {output_dir}/chunk_{idx}.tables.json  список таблиц

Контракт DocumentChunk заполняется чтением этих файлов после возврата worker'а
(или после in-process прогона).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from pump_calculator.etl.pdf.splitter import ChunkSpec


@dataclass
class DocumentChunk:
    """Результат прогона одного PDF-чанка через docling.

    Атрибуты:
        source_pdf:    исходный (полный) PDF
        chunk_pdf:     PDF этого чанка (нарезка splitter'а)
        page_start:    1-based первая страница чанка в исходном PDF
        page_end:      1-based последняя страница чанка
        markdown:      markdown-экспорт документа (включая таблицы)
        tables:        сериализованные таблицы:
                       [{"page_no": int|None, "df": [[...]], "header": [...]}, ...]
        raw_json_path: путь к сохранённому raw docling JSON (для отладки/аудита)
        runtime_sec:   wall-time прогона (включая subprocess fork)
    """

    source_pdf: Path
    chunk_pdf: Path
    page_start: int
    page_end: int
    markdown: str
    tables: list[dict] = field(default_factory=list)
    raw_json_path: Path | None = None
    runtime_sec: float = 0.0


def _worker_artifact_paths(output_dir: Path, idx: int) -> tuple[Path, Path, Path]:
    """Пути к трём файлам, которые пишет _docling_worker."""
    return (
        output_dir / f"chunk_{idx}.json",
        output_dir / f"chunk_{idx}.md",
        output_dir / f"chunk_{idx}.tables.json",
    )


def _read_chunk_artifacts(
    chunk_spec: ChunkSpec,
    output_dir: Path,
    runtime_sec: float,
) -> DocumentChunk:
    """Собрать DocumentChunk из артефактов, записанных worker'ом."""
    json_path, md_path, tables_path = _worker_artifact_paths(output_dir, chunk_spec.chunk_index)

    markdown = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    tables: list[dict] = []
    if tables_path.exists():
        try:
            tables = json.loads(tables_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            tables = []

    return DocumentChunk(
        source_pdf=chunk_spec.source_pdf,
        chunk_pdf=chunk_spec.output_pdf,
        page_start=chunk_spec.page_start,
        page_end=chunk_spec.page_end,
        markdown=markdown,
        tables=tables,
        raw_json_path=json_path if json_path.exists() else None,
        runtime_sec=runtime_sec,
    )


def run_docling(
    chunk_spec: ChunkSpec,
    output_dir: Path | str,
    ocr_lang: tuple[str, ...] = ("en",),
    use_subprocess: bool = True,
) -> DocumentChunk:
    """Прогнать chunk через docling.

    Args:
        chunk_spec: результат `splitter.split_pdf` для одного чанка.
        output_dir: директория для артефактов worker'а
                    (chunk_{idx}.{json,md,tables.json}). Создаётся при необходимости.
        ocr_lang:   кортеж кодов языков (например ("en",) или ("ru","en")).
                    Передаётся в worker через повторяемый --ocr-lang.
                    Для Pedrollo VX достаточно "en" (vector text).
        use_subprocess: True (default) — запуск worker'а в отдельном процессе
                    (memory-safe, рекомендуется в production).
                    False — in-process для тестов и быстрых отладочных прогонов.

    Returns:
        DocumentChunk с заполненным markdown, tables и путями артефактов.

    Raises:
        subprocess.CalledProcessError: если worker завершился с ненулевым кодом.
        FileNotFoundError: если ожидаемые артефакты не найдены после прогона.
    """
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()

    if use_subprocess:
        cmd = [
            sys.executable,
            "-m",
            "pump_calculator.etl.pdf._docling_worker",
            "--chunk-pdf",
            str(chunk_spec.output_pdf),
            "--output-dir",
            str(out_dir),
            "--idx",
            str(chunk_spec.chunk_index),
        ]
        for lang in ocr_lang:
            cmd.extend(["--ocr-lang", lang])
        # check=True гарантирует, что мы заметим падение worker'а
        subprocess.run(cmd, check=True)
    else:
        # In-process — для тестов: тот же worker, но без fork.
        from pump_calculator.etl.pdf import _docling_worker
        argv = [
            "--chunk-pdf",
            str(chunk_spec.output_pdf),
            "--output-dir",
            str(out_dir),
            "--idx",
            str(chunk_spec.chunk_index),
        ]
        for lang in ocr_lang:
            argv.extend(["--ocr-lang", lang])
        rc = _docling_worker.main(argv)
        if rc != 0:
            raise RuntimeError(f"_docling_worker.main returned non-zero: {rc}")

    runtime = time.perf_counter() - started

    md_path = out_dir / f"chunk_{chunk_spec.chunk_index}.md"
    if not md_path.exists():
        raise FileNotFoundError(
            f"docling worker did not produce expected artifact: {md_path}"
        )

    return _read_chunk_artifacts(chunk_spec, out_dir, runtime_sec=runtime)
