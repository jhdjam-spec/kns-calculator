"""Оркестрация ETL Phase 6: PDF-каталог → validated RawPumpRecord[].

Pipeline:
    1. ``splitter.split_pdf`` → list[ChunkSpec]
    2. ``pdfplumber_runner.run_pdfplumber`` (default) или
       ``docling_runner.run_docling`` (если runner="docling") → list[DocumentChunk]
    3. ``table_extractor.extract_pumps_from_chunks`` → list[RawPumpDraft]
    4. ``qh_extractor.extract_qh_curves_from_chunks`` → dict[model, list[QHPoint]]
    5. Сшивка drafts + curves по имени модели → list[RawPumpRecord]
    6. Pydantic-валидация → (validated, quarantine)
    7. Запись артефактов в ``runs/<run_id>/0X_*``
    8. Diff-отчёт (review.py) сравнивает с существующим pumps.json

Все артефакты прогона сохраняются в ``runs/<timestamp>/`` (gitignored)
для трассируемости и аудита.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from pump_calculator.etl.pdf.docling_runner import DocumentChunk, run_docling
from pump_calculator.etl.pdf.ksb_extractor import (
    extract_ksb_pumps_from_chunks,
    extract_ksb_qh_curves_from_chunks,
)
from pump_calculator.etl.pdf.pdfplumber_runner import run_pdfplumber
from pump_calculator.etl.pdf.qh_extractor import extract_qh_curves_from_chunks
from pump_calculator.etl.pdf.splitter import split_pdf
from pump_calculator.etl.pdf.table_extractor import (
    RawPumpDraft,
    extract_pumps_from_chunks,
)
from pump_calculator.etl.schemas import RawPumpRecord


def _select_extractor(brand: str):
    """Выбрать pump extractor по бренду.

    Pedrollo, Wilo, generic → table_extractor (rule-based табличный)
    KSB → ksb_extractor (специализированный для KRT designation tables)
    Будущее: Antarus, KAIQUAN — отдельные модули
    """
    if brand.upper() == "KSB":
        return extract_ksb_pumps_from_chunks
    return lambda chunks, brand_hint: extract_pumps_from_chunks(
        chunks, brand_hint=brand_hint, use_llm=False
    )


def _select_qh_extractor(brand: str):
    """Выбрать Q-H extractor по бренду.

    Pedrollo, generic → qh_extractor (численные таблицы Q-H)
    KSB → ksb stub Q-H (envelope-based parabolic, требует review)
    """
    if brand.upper() == "KSB":
        return extract_ksb_qh_curves_from_chunks
    return extract_qh_curves_from_chunks


@dataclass
class ParseResult:
    """Результат прогона ETL pipeline на одном PDF.

    Атрибуты:
        run_dir:      директория run/<timestamp>/ со всеми артефактами
        validated:    список raw-записей формата pumps.json (готовы к merge_into_pumps_json)
        quarantine:   draft'ы, которые не прошли Pydantic-валидацию RawPumpRecord
                      (нет qh_curve, или другие проблемы)
        diff_md:      markdown diff-отчёт сравнения с существующим pumps.json
        errors:       список текстовых ошибок этапов pipeline
        runtime_sec:  суммарное время прогона
    """

    run_dir: Path
    validated: list[dict] = field(default_factory=list)
    quarantine: list[dict] = field(default_factory=list)
    diff_md: str = ""
    errors: list[str] = field(default_factory=list)
    runtime_sec: float = 0.0


def _make_run_id() -> str:
    """Идентификатор прогона: ISO timestamp + короткий хеш."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    rnd = hashlib.sha1(str(time.time()).encode()).hexdigest()[:6]
    return f"{ts}-{rnd}"


def _hash_file(path: Path) -> str:
    """SHA-256 файла (полный, для аудита источника)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _draft_to_raw_dict(
    draft: RawPumpDraft,
    qh_points: list,
    source_label: str,
) -> dict:
    """Конвертировать RawPumpDraft + qh_curve в dict формата RawPumpRecord.

    qh_points: list[QHPoint] из qh_extractor.

    Здесь НЕ вызываем importer.import_raw_pump — он работает с pydantic
    RawPumpRecord. Сначала собираем dict, валидируем через RawPumpRecord
    (это и есть quarantine-фильтр), и только потом вызываем importer
    в pipeline (Шаг 5 → step 7).
    """
    return {
        "brand": draft.brand,
        "model": draft.model,
        "type": draft.type,
        "impeller": draft.impeller,
        "free_passage_mm": draft.free_passage_mm,
        "qh_curve": [
            {
                "Q_m3h": p.Q_m3h,
                "H_m": p.H_m,
                **({"eta_pct": p.eta_pct} if p.eta_pct is not None else {}),
                **({"P_kW": p.P_kW} if p.P_kW is not None else {}),
                **({"NPSHr_m": p.NPSHr_m} if p.NPSHr_m is not None else {}),
            }
            for p in qh_points
        ],
        "P_kW": draft.P_kW,
        "voltage_v": draft.voltage_v,
        "phase": draft.phase,
        "ip_rating": draft.ip_rating,
        "discharge_DN_mm": draft.discharge_DN_mm,
        "wastewater_compat": draft.wastewater_compat,
        "price_segment": draft.price_segment,
        "available_ru_status": draft.available_ru_status,
        "distributor": draft.distributor,
        "warranty_months": draft.warranty_months,
        "source": source_label,
    }


def parse_catalog(
    pdf_path: Path | str,
    brand: str,
    runs_root: Path | str,
    runner: Literal["pdfplumber", "docling"] = "pdfplumber",
    pages_per_chunk: int = 4,
) -> ParseResult:
    """Прогнать полный ETL на одном PDF-каталоге.

    Args:
        pdf_path: путь к PDF-каталогу.
        brand: бренд для проставления в RawPumpDraft.brand (Pedrollo, KAIQUAN, ...).
        runs_root: корневая директория для прогонов (обычно ``backend/runs``).
        runner: "pdfplumber" (default) для vector-text PDF или "docling" для
                сканов/OCR. Pedrollo, Wilo, KSB — vector, KAIQUAN — может
                требовать docling.
        pages_per_chunk: размер чанка для splitter.

    Returns:
        ParseResult с validated[], quarantine[], diff_md, errors[].

    Артефакты в ``runs_root/<run_id>/``:
        - input.pdf                копия исходника
        - meta.json                {pdf_hash, runner, timestamp, ...}
        - 01_chunks/               вырезанные PDF-чанки
        - 02_extract/              chunk_*.{md,tables.json} — вывод runner'а
        - 03_drafts.json           RawPumpDraft[] (без qh_curve)
        - 04_curves.json           dict[model, list[QHPoint]]
        - 05_validated.json        list[RawPumpRecord-dict] прошедшие валидацию
        - 06_quarantine.json       draft'ы, упавшие на валидации
        - 07_diff.md               diff-отчёт vs существующий pumps.json
    """
    started = time.perf_counter()
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    runs_root = Path(runs_root).resolve()
    run_id = _make_run_id()
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # 0. meta + копия исходника
    pdf_copy = run_dir / "input.pdf"
    shutil.copy2(pdf_path, pdf_copy)
    meta = {
        "run_id": run_id,
        "started_at": datetime.now().isoformat(),
        "pdf_path": str(pdf_path),
        "pdf_sha256": _hash_file(pdf_path),
        "brand": brand,
        "runner": runner,
        "pages_per_chunk": pages_per_chunk,
    }
    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    errors: list[str] = []
    validated: list[dict] = []
    quarantine: list[dict] = []

    # 1. Split
    chunks_dir = run_dir / "01_chunks"
    chunks_dir.mkdir(exist_ok=True)
    chunks = split_pdf(pdf_path, chunks_dir, pages_per_chunk=pages_per_chunk)

    # 2. Extract via chosen runner
    extract_dir = run_dir / "02_extract"
    extract_dir.mkdir(exist_ok=True)
    document_chunks: list[DocumentChunk] = []
    for chunk in chunks:
        try:
            if runner == "docling":
                doc_chunk = run_docling(chunk, output_dir=extract_dir)
            else:
                doc_chunk = run_pdfplumber(chunk, output_dir=extract_dir)
            document_chunks.append(doc_chunk)
        except Exception as e:  # noqa: BLE001
            errors.append(f"Runner {runner} failed on chunk {chunk.chunk_index}: {e}")

    if not document_chunks:
        return ParseResult(
            run_dir=run_dir,
            errors=errors + ["No DocumentChunks were produced"],
            runtime_sec=time.perf_counter() - started,
        )

    # 3. Extract pump drafts (выбираем extractor по бренду)
    extractor = _select_extractor(brand)
    drafts = extractor(document_chunks, brand)
    drafts_path = run_dir / "03_drafts.json"
    drafts_path.write_text(
        json.dumps(
            [d.model_dump() for d in drafts],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # 4. Extract Q-H curves (выбираем Q-H extractor по бренду)
    qh_extractor = _select_qh_extractor(brand)
    curves = qh_extractor(document_chunks)
    curves_path = run_dir / "04_curves.json"
    curves_path.write_text(
        json.dumps(
            {
                model: [{"Q_m3h": p.Q_m3h, "H_m": p.H_m} for p in pts]
                for model, pts in curves.items()
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # 5. Сшивка + Pydantic-валидация → validated/quarantine
    source_label = f"{runner}-{brand.lower()}-{datetime.now().strftime('%Y-%m')}"
    for draft in drafts:
        qh_points = curves.get(draft.model, [])
        raw_dict = _draft_to_raw_dict(draft, qh_points, source_label)
        try:
            # Валидация: модель RawPumpRecord проверит обязательные поля
            # (qh_curve минимум 3 точки, free_passage_mm в [0, 200], P_kW > 0)
            RawPumpRecord.model_validate(raw_dict)
            validated.append(raw_dict)
        except Exception as e:  # noqa: BLE001
            quarantine.append({"draft": raw_dict, "error": str(e)})

    # 6. Сохранить validated и quarantine
    (run_dir / "05_validated.json").write_text(
        json.dumps(validated, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "06_quarantine.json").write_text(
        json.dumps(quarantine, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 7. Diff-отчёт (импорт review здесь, чтобы избежать циклов)
    from pump_calculator.etl.review import build_diff_report

    diff_md = build_diff_report(validated, brand=brand)
    (run_dir / "07_diff.md").write_text(diff_md, encoding="utf-8")

    return ParseResult(
        run_dir=run_dir,
        validated=validated,
        quarantine=quarantine,
        diff_md=diff_md,
        errors=errors,
        runtime_sec=round(time.perf_counter() - started, 2),
    )
