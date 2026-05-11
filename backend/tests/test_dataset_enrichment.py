"""Тесты dataset enrichment pipeline — категоризация по confidence.

Покрывает:
- confidence ≥ 0.7 → auto_accepted, запись в etalons_uploaded.jsonl
- 0.5 ≤ confidence < 0.7 → queued, файл в _queue/
- confidence < 0.5 → archived_only, никаких записей в dataset
- approve queued → перенос в jsonl
- merge_to_etalons → дедупликация по project_code и (Q,H,city)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pump_calculator.etl.dataset_enrichment import (
    STATUS_ARCHIVED_ONLY,
    STATUS_AUTO_ACCEPTED,
    STATUS_QUEUED,
    DatasetEnricher,
)


@pytest.fixture
def enricher(tmp_path: Path) -> DatasetEnricher:
    """Чистый DatasetEnricher с tmp_path вместо реального 02_dataset."""
    return DatasetEnricher(dataset_root=tmp_path)


# ---------------------------------------------------------------------------
# Categorize
# ---------------------------------------------------------------------------


def test_categorize_high_confidence_auto_accepted(enricher: DatasetEnricher):
    assert enricher.categorize(0.75) == STATUS_AUTO_ACCEPTED
    assert enricher.categorize(1.0) == STATUS_AUTO_ACCEPTED


def test_categorize_mid_confidence_queued(enricher: DatasetEnricher):
    assert enricher.categorize(0.5) == STATUS_QUEUED
    assert enricher.categorize(0.69) == STATUS_QUEUED


def test_categorize_low_confidence_archived_only(enricher: DatasetEnricher):
    assert enricher.categorize(0.25) == STATUS_ARCHIVED_ONLY
    assert enricher.categorize(0.0) == STATUS_ARCHIVED_ONLY


# ---------------------------------------------------------------------------
# process_upload
# ---------------------------------------------------------------------------


def test_process_upload_auto_accepted_appends_jsonl(enricher: DatasetEnricher):
    """confidence=1.0 → запись попадает в etalons_uploaded.jsonl."""
    parsed = {
        "Q_m3h": 88.6,
        "dH_m": 39.0,
        "city": "Краснодар",
        "wastewater_type": "domestic",
        "confidence": 1.0,
        "project_code": "1578-22-НК",
    }
    res = enricher.process_upload(parsed, raw_text="...", s3_key="tz_archive/2026/05/11/x.txt")
    assert res["status"] == STATUS_AUTO_ACCEPTED
    assert res["jsonl_appended"] is True
    assert res["error"] is None
    assert enricher.jsonl_path.exists()
    lines = enricher.jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["Q_m3h"] == 88.6
    assert rec["project_code"] == "1578-22-НК"
    assert rec["source"] == "user_import"
    assert rec["s3_key"] == "tz_archive/2026/05/11/x.txt"


def test_process_upload_queued_writes_queue_file(enricher: DatasetEnricher):
    """confidence=0.6 → файл в _queue/<id>.json с raw_text."""
    parsed = {"Q_m3h": 50, "dH_m": 15, "confidence": 0.6}
    res = enricher.process_upload(
        parsed, raw_text="Q=50 м³/ч H=15 м", s3_key=None, upload_id="upload-test-1"
    )
    assert res["status"] == STATUS_QUEUED
    assert res["jsonl_appended"] is False
    queue_file = enricher.queue_dir / "upload-test-1.json"
    assert queue_file.exists()
    data = json.loads(queue_file.read_text(encoding="utf-8"))
    assert data["raw_text"] == "Q=50 м³/ч H=15 м"
    assert data["confidence"] == 0.6
    assert data["status"] == STATUS_QUEUED
    # JSONL не должен быть создан
    assert not enricher.jsonl_path.exists()


def test_process_upload_low_confidence_archived_only(enricher: DatasetEnricher):
    """confidence=0.25 → status=archived_only, ничего в dataset не пишется."""
    parsed = {"Q_m3h": 10, "confidence": 0.25}
    res = enricher.process_upload(parsed, raw_text="vague", s3_key=None)
    assert res["status"] == STATUS_ARCHIVED_ONLY
    assert res["jsonl_appended"] is False
    assert res["record_path"] is None
    # Никакие dirs не должны быть созданы (опционально, depends на impl)
    assert not enricher.jsonl_path.exists()


# ---------------------------------------------------------------------------
# Approve / Reject
# ---------------------------------------------------------------------------


def test_approve_moves_queue_to_jsonl(enricher: DatasetEnricher):
    """Approve удаляет queue-файл и добавляет в jsonl."""
    parsed = {"Q_m3h": 60, "confidence": 0.55}
    enricher.process_upload(
        parsed, raw_text="rt", s3_key=None, upload_id="upload-approve-test"
    )
    queue_file = enricher.queue_dir / "upload-approve-test.json"
    assert queue_file.exists()

    res = enricher.approve("upload-approve-test")
    assert res["ok"] is True
    assert res["record"]["status"] == "approved"
    assert "approved_at" in res["record"]
    assert not queue_file.exists()  # удалён
    assert enricher.jsonl_path.exists()
    rec = json.loads(enricher.jsonl_path.read_text(encoding="utf-8").strip())
    assert rec["status"] == "approved"
    # raw_text должен быть удалён из JSONL-записи
    assert "raw_text" not in rec


def test_approve_unknown_returns_error(enricher: DatasetEnricher):
    res = enricher.approve("nonexistent-id")
    assert res["ok"] is False
    assert "not in queue" in res["error"]


# ---------------------------------------------------------------------------
# merge_to_etalons
# ---------------------------------------------------------------------------


def test_merge_to_etalons_dedup_by_project_code(enricher: DatasetEnricher, tmp_path: Path):
    """Запись с уже существующим project_code в public должна skip'нуться."""
    # Подготовка: одна запись в public_etalons (с code "СКЯ-23/24-НВК")
    public_dir = tmp_path / "etalons" / "public"
    public_dir.mkdir(parents=True)
    (public_dir / "etalons_public_2026-05-09.json").write_text(
        json.dumps([{"code": "СКЯ-23/24-НВК", "Q_m3h": 100, "H_m": 50}]),
        encoding="utf-8",
    )
    # Две загруженные: одна дубль, одна новая
    enricher._ensure_dirs()
    enricher._append_jsonl(
        {
            "id": "u1",
            "project_code": "СКЯ-23/24-НВК",
            "Q_m3h": 100,
            "dH_m": 50,
            "city": "Волноваха",
            "confidence": 1.0,
        }
    )
    enricher._append_jsonl(
        {
            "id": "u2",
            "project_code": "NEW-001",
            "Q_m3h": 25,
            "dH_m": 12,
            "city": "Казань",
            "confidence": 1.0,
        }
    )
    res = enricher.merge_to_etalons()
    assert res["error"] is None
    assert res["merged_count"] == 1  # только u2
    assert res["skipped_dedup"] == 1  # u1 дубль
    out = json.loads(Path(res["output_path"]).read_text(encoding="utf-8"))
    assert len(out) == 1
    assert out[0]["project_code"] == "NEW-001"
