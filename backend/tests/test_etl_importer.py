"""Тесты Phase 5: ETL importer."""

from __future__ import annotations

import json

import pytest

from pump_calculator.etl.importer import (
    _make_pump_id,
    import_raw_pump,
    import_raw_pumps_from_json,
    merge_into_pumps_json,
)
from pump_calculator.etl.schemas import QHPoint, RawPumpRecord

# ----- Фикстуры -----

@pytest.fixture
def kaiquan_raw() -> RawPumpRecord:
    """Raw-запись для KAIQUAN 65WQ/S 30-22-5.5 (вымышленные данные)."""
    return RawPumpRecord(
        brand="KAIQUAN",
        model="65WQ/S 30-22-5.5",
        type="submersible_sewage",
        impeller="single-channel",
        free_passage_mm=65,
        qh_curve=[
            QHPoint(Q_m3h=0, H_m=30, eta_pct=0, NPSHr_m=1.5),
            QHPoint(Q_m3h=15, H_m=28, eta_pct=35.0, NPSHr_m=1.8),
            QHPoint(Q_m3h=30, H_m=25, eta_pct=50.0, NPSHr_m=2.5),
            QHPoint(Q_m3h=45, H_m=20, eta_pct=48.0, NPSHr_m=4.0),
            QHPoint(Q_m3h=60, H_m=12, eta_pct=32.0, NPSHr_m=6.0),
        ],
        P_kW=5.5,
        discharge_DN_mm=65,
        wastewater_compat=["domestic", "industrial"],
        price_segment="budget",
        available_ru_status="official",
        distributor="АСО (acorussia.ru)",
        warranty_months=18,
        source="test-fixture-2026-05",
    )


# ----- _make_pump_id -----

def test_make_pump_id_simple():
    assert _make_pump_id("KAIQUAN", "50WQ/S202-3") == "kaiquan-50wq-s202-3"


def test_make_pump_id_with_spaces():
    assert _make_pump_id("Wilo", "Wilo-Rexa PRO V05") == "wilo-wilo-rexa-pro-v05"


def test_make_pump_id_with_special_chars():
    assert _make_pump_id("KSB", "Amarex N S 50-220") == "ksb-amarex-n-s-50-220"


# ----- import_raw_pump -----

def test_import_returns_proper_structure(kaiquan_raw):
    pump = import_raw_pump(kaiquan_raw)

    assert pump["id"] == "kaiquan-65wq-s-30-22-5-5"
    assert pump["brand"] == "KAIQUAN"
    assert pump["type"] == "submersible_sewage"
    assert pump["impeller"] == "single-channel"
    assert pump["free_passage_mm"] == 65


def test_import_calculates_envelope(kaiquan_raw):
    pump = import_raw_pump(kaiquan_raw)
    env = pump["envelope"]

    assert env["Q_min_m3h"] == 0
    assert env["Q_max_m3h"] == 60
    assert env["H_min_m"] == 12
    assert env["H_max_m"] == 30
    # BEP должен быть около 30 (там eta=50)
    assert env["Q_BEP_m3h"] is not None
    assert 25 < env["Q_BEP_m3h"] < 40


def test_import_preserves_qh_curve(kaiquan_raw):
    pump = import_raw_pump(kaiquan_raw)
    assert len(pump["qh_curve"]) == 5
    assert pump["qh_curve"][0]["Q_m3h"] == 0
    assert pump["qh_curve"][2]["eta_pct"] == 50.0
    assert pump["qh_curve"][2]["NPSHr_m"] == 2.5


def test_import_sets_engineer_flag_to_review(kaiquan_raw):
    """Все импортированные → needs_review (требует проверки человеком)."""
    pump = import_raw_pump(kaiquan_raw)
    assert pump["_engineer_flag"] == "needs_review"
    assert pump["_engineer_note"] is not None


def test_import_sets_added_updated_dates(kaiquan_raw):
    pump = import_raw_pump(kaiquan_raw)
    assert "_added" in pump
    assert "_updated" in pump
    # ISO format YYYY-MM-DD
    assert len(pump["_added"]) == 10


def test_import_keeps_source(kaiquan_raw):
    pump = import_raw_pump(kaiquan_raw)
    assert pump["_source"] == "test-fixture-2026-05"


# ----- import_raw_pumps_from_json -----

def test_import_from_json_file(kaiquan_raw, tmp_path):
    file = tmp_path / "raw.json"
    file.write_text(
        json.dumps([kaiquan_raw.model_dump()], ensure_ascii=False),
        encoding="utf-8",
    )
    result = import_raw_pumps_from_json(file)
    assert len(result) == 1
    assert result[0]["brand"] == "KAIQUAN"


def test_import_from_json_validates_records(tmp_path):
    """Если запись битая — внятная ошибка с номером записи."""
    file = tmp_path / "bad.json"
    bad = [{"brand": "KAIQUAN"}]  # отсутствуют обязательные поля
    file.write_text(json.dumps(bad), encoding="utf-8")

    with pytest.raises(ValueError, match="Record #0"):
        import_raw_pumps_from_json(file)


def test_import_from_json_requires_array(tmp_path):
    file = tmp_path / "obj.json"
    file.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Expected JSON array"):
        import_raw_pumps_from_json(file)


# ----- merge_into_pumps_json -----

def test_merge_appends_new_records(kaiquan_raw, tmp_path):
    pumps_file = tmp_path / "pumps.json"
    pumps_file.write_text(json.dumps({"pumps": []}), encoding="utf-8")

    new_pumps = [import_raw_pump(kaiquan_raw)]
    added, skipped = merge_into_pumps_json(new_pumps, pumps_file)

    assert added == 1
    assert skipped == 0

    saved = json.loads(pumps_file.read_text(encoding="utf-8"))
    assert len(saved["pumps"]) == 1


def test_merge_skips_duplicates_by_default(kaiquan_raw, tmp_path):
    pumps_file = tmp_path / "pumps.json"
    existing = [import_raw_pump(kaiquan_raw)]
    pumps_file.write_text(
        json.dumps({"pumps": existing}, ensure_ascii=False),
        encoding="utf-8",
    )

    new_pumps = [import_raw_pump(kaiquan_raw)]
    added, skipped = merge_into_pumps_json(new_pumps, pumps_file)

    assert added == 0
    assert skipped == 1


def test_merge_overwrites_with_flag(kaiquan_raw, tmp_path):
    pumps_file = tmp_path / "pumps.json"
    existing = [import_raw_pump(kaiquan_raw)]
    pumps_file.write_text(
        json.dumps({"pumps": existing}, ensure_ascii=False),
        encoding="utf-8",
    )

    new_pumps = [import_raw_pump(kaiquan_raw)]
    added, skipped = merge_into_pumps_json(new_pumps, pumps_file, overwrite=True)

    assert added == 1
    assert skipped == 0
