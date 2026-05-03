"""Тесты Antarus НК extractor (Phase 6.7).

Antarus уникален тем, что Q, H, free_passage, P_kW закодированы прямо
в имени модели. PDF (с-о-к.ru мирор) использует font mapping HK→НК.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pump_calculator.etl.pdf.antarus_extractor import (
    ANTARUS_MODEL_RE,
    _build_stub_qh_curve,
    _classify_impeller,
    _normalize_series,
    extract_antarus_pumps_from_chunks,
    extract_antarus_qh_curves_from_chunks,
)
from pump_calculator.etl.pdf.pdfplumber_runner import run_pdfplumber
from pump_calculator.etl.pdf.splitter import split_pdf

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "antarus_nk_2023.pdf"


# ----- Regex unit-tests (быстрые) -----------------------------------------


def test_antarus_regex_matches_simple_model() -> None:
    """HK1-50-10-10-0,75-10M парсится корректно."""
    m = ANTARUS_MODEL_RE.search("HK1-50-10-10-0,75-10M 938004 1,68 0,75 2 0,839")
    assert m is not None
    assert m.group("series") == "HK1"
    assert m.group("q") == "50"
    assert m.group("h") == "10"
    assert m.group("passage") == "10"
    assert m.group("p_kw") == "0,75"
    assert m.group("variant") is None
    assert m.group("depth") == "10"


def test_antarus_regex_matches_tb_variant() -> None:
    """TB вариант (HK1-100-15-65-5,5-TB-10M)."""
    m = ANTARUS_MODEL_RE.search("HK1-100-15-65-5,5-TB-10M 938057")
    assert m is not None
    assert m.group("series") == "HK1"
    assert m.group("variant") == "TB"
    assert m.group("p_kw") == "5,5"


def test_antarus_regex_matches_cyrillic_series() -> None:
    """НК2-300-23-1000-90-TB-10М с кириллицей М на конце."""
    m = ANTARUS_MODEL_RE.search("НК2-300-23-1000-90-TB-10М")
    assert m is not None
    assert m.group("series") == "НК2"
    assert m.group("q") == "300"
    assert m.group("h") == "23"
    assert m.group("passage") == "1000"


def test_antarus_regex_skips_non_model() -> None:
    """Случайный текст не матчится."""
    assert ANTARUS_MODEL_RE.search("Page 10 of 47") is None
    assert ANTARUS_MODEL_RE.search("Таблица 12") is None


def test_normalize_series_converts_hk_to_nk() -> None:
    """HK1 → НК1, HK2 → НК2."""
    assert _normalize_series("HK1") == "НК1"
    assert _normalize_series("HK2") == "НК2"
    assert _normalize_series("НК1") == "НК1"  # idempotent


# ----- Impeller classification --------------------------------------------


def test_classify_impeller_nk1_is_single_channel() -> None:
    """НК1 — одноканальное закрытое."""
    assert _classify_impeller("НК1", q=50, passage=30) == "single-channel"
    assert _classify_impeller("НК1", q=100, passage=10) == "single-channel"


def test_classify_impeller_nk2_small_passage_is_vortex() -> None:
    """НК2 с малым passage → vortex (предочищенные)."""
    assert _classify_impeller("НК2", q=200, passage=15) == "vortex"


def test_classify_impeller_nk2_large_passage_is_multi() -> None:
    """НК2 с большим passage → multi-channel."""
    assert _classify_impeller("НК2", q=300, passage=80) == "multi-channel"


# ----- Stub Q-H curve -----------------------------------------------------


def test_stub_qh_returns_5_points() -> None:
    """5 опорных точек."""
    points = _build_stub_qh_curve(q_nom=50.0, h_nom=10.0)
    assert len(points) == 5
    qs = [p.Q_m3h for p in points]
    assert qs == sorted(qs)  # Q монотонно растёт
    hs = [p.H_m for p in points]
    assert hs[0] > hs[-1]  # H падает (физика)
    # Shutoff = 1.25 × H_nom = 12.5
    assert hs[0] == pytest.approx(12.5)


def test_stub_qh_h_at_q_nom_close_to_nominal() -> None:
    """В Q=Q_nom (3-я точка) H близок к H_nom."""
    points = _build_stub_qh_curve(q_nom=100.0, h_nom=20.0)
    h_at_nom = points[2].H_m
    # H_shutoff=25, при Q/Q_runout = 100/150 = 0.667 → H = 25*(1-0.7*0.444) = 25*0.689 = 17.2
    assert 15 <= h_at_nom <= 22


# ----- Pipeline integration tests -----------------------------------------


@pytest.fixture(scope="module")
def antarus_chunks(tmp_path_factory: pytest.TempPathFactory) -> list:
    """Один прогон pdfplumber для всех тестов модуля."""
    base = tmp_path_factory.mktemp("antarus_test")
    chunks = split_pdf(FIXTURE_PDF, base / "chunks", pages_per_chunk=10)
    return [run_pdfplumber(c, output_dir=base / "plumber") for c in chunks]


def test_antarus_extractor_finds_at_least_30_models(antarus_chunks) -> None:
    """Antarus НК каталог содержит десятки типоразмеров."""
    drafts = extract_antarus_pumps_from_chunks(antarus_chunks, brand_hint="Antarus")
    assert len(drafts) >= 30, f"ожидаем ≥30 моделей, получили {len(drafts)}"


def test_antarus_extractor_brand_correct(antarus_chunks) -> None:
    """brand='Antarus'."""
    drafts = extract_antarus_pumps_from_chunks(antarus_chunks, brand_hint="Antarus")
    assert all(d.brand == "Antarus" for d in drafts)


def test_antarus_extractor_models_normalized_to_cyrillic(antarus_chunks) -> None:
    """Все имена моделей содержат НК (не HK)."""
    drafts = extract_antarus_pumps_from_chunks(antarus_chunks, brand_hint="Antarus")
    for d in drafts:
        assert "НК" in d.model, f"non-Cyrillic model: {d.model}"
        assert "HK" not in d.model, f"unormalized HK in model: {d.model}"


def test_antarus_extractor_price_segment_is_mid(antarus_chunks) -> None:
    """Antarus — российский средний сегмент."""
    drafts = extract_antarus_pumps_from_chunks(antarus_chunks, brand_hint="Antarus")
    assert all(d.price_segment == "mid" for d in drafts)


def test_antarus_extractor_p_kw_reasonable(antarus_chunks) -> None:
    """Мощность 0.55-200 кВт (реальный диапазон серии)."""
    drafts = extract_antarus_pumps_from_chunks(antarus_chunks, brand_hint="Antarus")
    for d in drafts:
        assert 0.5 <= d.P_kW <= 200, f"{d.model}: P_kW={d.P_kW}"


def test_antarus_qh_curves_generated(antarus_chunks) -> None:
    """Stub Q-H для всех Antarus моделей."""
    drafts = extract_antarus_pumps_from_chunks(antarus_chunks, brand_hint="Antarus")
    curves = extract_antarus_qh_curves_from_chunks(antarus_chunks)
    drafts_models = {d.model for d in drafts}
    curves_models = set(curves.keys())
    assert drafts_models == curves_models


def test_antarus_extractor_notes_mention_review(antarus_chunks) -> None:
    """Все Antarus drafts помечены NEEDS REVIEW."""
    drafts = extract_antarus_pumps_from_chunks(antarus_chunks, brand_hint="Antarus")
    for d in drafts:
        assert d.notes and "review" in d.notes.lower()
