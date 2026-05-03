"""End-to-end тесты ETL pipeline (Phase 6.4).

Прогоняем `parse_catalog` на Pedrollo VX 50 Hz datasheet и проверяем все
этапы: split → pdfplumber → drafts → curves → validated → diff.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pump_calculator.etl.pipeline import ParseResult, parse_catalog
from pump_calculator.etl.review import build_diff_report

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "pedrollo_vx_50hz.pdf"


@pytest.fixture(scope="module")
def pedrollo_run(tmp_path_factory: pytest.TempPathFactory) -> ParseResult:
    """Один прогон pipeline для всех тестов модуля."""
    runs_root = tmp_path_factory.mktemp("etl_runs")
    return parse_catalog(
        pdf_path=FIXTURE_PDF,
        brand="Pedrollo",
        runs_root=runs_root,
        runner="pdfplumber",
        pages_per_chunk=4,
    )


def test_pipeline_creates_run_dir_with_artifacts(pedrollo_run: ParseResult) -> None:
    """run_dir содержит все 8 ожидаемых артефактов прогона."""
    expected = [
        "input.pdf",
        "meta.json",
        "01_chunks",
        "02_extract",
        "03_drafts.json",
        "04_curves.json",
        "05_validated.json",
        "06_quarantine.json",
        "07_diff.md",
    ]
    for name in expected:
        path = pedrollo_run.run_dir / name
        assert path.exists(), f"missing artifact: {path}"


def test_pipeline_validates_at_least_8_models(pedrollo_run: ParseResult) -> None:
    """Минимум 8 моделей Pedrollo VX должны пройти Pydantic-валидацию."""
    assert len(pedrollo_run.validated) >= 8, (
        f"expected ≥8 validated, got {len(pedrollo_run.validated)}, "
        f"quarantine={len(pedrollo_run.quarantine)}, errors={pedrollo_run.errors}"
    )


def test_pipeline_validated_have_qh_curves(pedrollo_run: ParseResult) -> None:
    """Каждая validated-запись имеет qh_curve минимум 3 точки (требование RawPumpRecord)."""
    for rec in pedrollo_run.validated:
        assert "qh_curve" in rec
        assert len(rec["qh_curve"]) >= 3, (
            f"{rec['model']}: только {len(rec['qh_curve'])} точек Q-H"
        )


def test_pipeline_validated_have_required_fields(pedrollo_run: ParseResult) -> None:
    """Обязательные поля RawPumpRecord присутствуют."""
    for rec in pedrollo_run.validated:
        assert rec["brand"] == "Pedrollo"
        assert rec["model"]
        assert rec["P_kW"] > 0
        assert rec["free_passage_mm"] >= 0
        assert rec["voltage_v"] in (220, 230, 380, 400)
        assert rec["phase"] in (1, 3)


def test_pipeline_diff_report_is_markdown(pedrollo_run: ParseResult) -> None:
    """diff_md содержит markdown-заголовок и упоминание Pedrollo."""
    assert pedrollo_run.diff_md.startswith("# ETL diff-отчёт")
    assert "Pedrollo" in pedrollo_run.diff_md


def test_pipeline_meta_has_pdf_hash(pedrollo_run: ParseResult) -> None:
    """meta.json содержит SHA-256 хеш входного PDF (для аудита)."""
    meta = json.loads((pedrollo_run.run_dir / "meta.json").read_text(encoding="utf-8"))
    assert "pdf_sha256" in meta
    assert len(meta["pdf_sha256"]) == 64  # SHA-256 hex
    assert meta["brand"] == "Pedrollo"
    assert meta["runner"] == "pdfplumber"


def test_pipeline_no_errors_on_pedrollo(pedrollo_run: ParseResult) -> None:
    """На Pedrollo VX (vector text) не должно быть никаких ошибок runner'а."""
    assert pedrollo_run.errors == [], (
        f"unexpected errors on Pedrollo VX: {pedrollo_run.errors}"
    )


def test_pipeline_missing_pdf_raises(tmp_path: Path) -> None:
    """parse_catalog на несуществующий PDF → FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        parse_catalog(
            pdf_path=tmp_path / "nope.pdf",
            brand="Pedrollo",
            runs_root=tmp_path / "runs",
        )


# ----- review.py ----------------------------------------------------------


def test_review_build_diff_report_structure(pedrollo_run: ParseResult) -> None:
    """diff-отчёт всегда содержит секции (новые / совпадения / только в БД)."""
    diff = build_diff_report(pedrollo_run.validated, brand="Pedrollo")
    assert "# ETL diff-отчёт" in diff
    assert "Pedrollo" in diff
    assert "Новые модели" in diff  # секция всегда упомянута в саммари
    assert "Совпадают по id" in diff
    assert "merge" in diff.lower()  # подсказка про команду merge


def test_review_handles_empty_validated() -> None:
    """build_diff_report не падает на пустом списке."""
    diff = build_diff_report([], brand="UnknownBrand")
    assert "Новые модели** (будут добавлены): 0" in diff
