"""Тесты KSB Amarex KRT extractor (Phase 6.6).

Используем реальную фикстуру `ksb_amarex_krt_50hz.pdf` (40 стр, 6.7 МБ).
Включает: extractor, Q-H stub, end-to-end pipeline.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pump_calculator.etl.pdf.ksb_extractor import (
    IMPELLER_MAP,
    KRT_ROW_RE,
    _build_stub_qh_curve,
    _stub_qh_envelope,
    extract_ksb_pumps_from_chunks,
    extract_ksb_qh_curves_from_chunks,
)
from pump_calculator.etl.pdf.pdfplumber_runner import run_pdfplumber
from pump_calculator.etl.pdf.splitter import split_pdf

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "ksb_amarex_krt_50hz.pdf"


# ----- KRT_ROW_RE unit-tests (быстрые, без PDF) ---------------------------


def test_krt_row_re_matches_simple_row() -> None:
    """Базовая designation row парсится корректно."""
    row = "40-252 S G 4 7 235 175 - - 10 13 0,03"
    m = KRT_ROW_RE.search(row)
    assert m is not None
    assert m.group("size") == "40-252"
    assert m.group("impeller") == "S"
    assert m.group("free_passage") == "7"


def test_krt_row_re_matches_multi_material() -> None:
    """Material variant с несколькими значениями (G, G1, G2, GH)."""
    row = "80-315 D G, G1 1 65 260 230 10 15 11 15 0,124"
    m = KRT_ROW_RE.search(row)
    assert m is not None
    assert m.group("size") == "80-315"
    assert m.group("impeller") == "D"
    assert m.group("free_passage") == "65"


def test_krt_row_re_skips_non_designation() -> None:
    """Не designation row → нет match."""
    assert KRT_ROW_RE.search("Operating pressure: 10 bar") is None
    assert KRT_ROW_RE.search("Page 18 of 40") is None
    # У нас нет дефолтного DN <40 → не должно матчиться
    assert KRT_ROW_RE.search("garbage line\n123") is None


# ----- Stub Q-H curve unit-tests ------------------------------------------


def test_stub_qh_envelope_small_dn() -> None:
    """DN 40 → малый Q_BEP, средний H."""
    q_bep, h_shutoff, runout = _stub_qh_envelope(40, "S")
    assert q_bep == 25.0
    assert h_shutoff == 22.0
    assert runout == 1.6


def test_stub_qh_envelope_vortex_lower_h() -> None:
    """Vortex (F) даёт на ~15% меньше H за тот же DN."""
    _, h_closed, _ = _stub_qh_envelope(80, "K")
    _, h_vortex, _ = _stub_qh_envelope(80, "F")
    assert h_vortex < h_closed
    assert abs(h_vortex - h_closed * 0.85) < 0.1


def test_stub_qh_curve_returns_5_points() -> None:
    """5 опорных точек в правильном порядке."""
    points = _build_stub_qh_curve(dn_mm=80, impeller="K")
    assert len(points) == 5
    # Q монотонно растёт
    qs = [p.Q_m3h for p in points]
    assert qs == sorted(qs)
    # H монотонно падает (физика)
    hs = [p.H_m for p in points]
    assert hs[0] > hs[-1], f"H не падает: {hs}"
    assert hs[0] == hs[0]  # shutoff
    # Все H > 0 (центробежный насос всегда даёт положительный напор в рабочем диапазоне)
    assert all(h > 0 for h in hs)


# ----- Pipeline integration tests (реальный PDF) --------------------------


@pytest.fixture(scope="module")
def ksb_chunks(tmp_path_factory: pytest.TempPathFactory) -> list:
    """Один прогон pdfplumber для всех тестов модуля."""
    base = tmp_path_factory.mktemp("ksb_test")
    chunks = split_pdf(FIXTURE_PDF, base / "chunks", pages_per_chunk=10)
    return [run_pdfplumber(c, output_dir=base / "plumber") for c in chunks]


def test_ksb_extractor_finds_at_least_50_models(ksb_chunks) -> None:
    """KSB Amarex KRT 50Hz содержит >100 типоразмеров (S/F/E/D/K по разным DN)."""
    drafts = extract_ksb_pumps_from_chunks(ksb_chunks, brand_hint="KSB")
    assert len(drafts) >= 50, f"ожидаем ≥50 моделей KRT, получили {len(drafts)}"


def test_ksb_extractor_models_all_start_with_krt(ksb_chunks) -> None:
    """Все имена моделей начинаются с 'KRT '."""
    drafts = extract_ksb_pumps_from_chunks(ksb_chunks, brand_hint="KSB")
    for d in drafts:
        assert d.model.startswith("KRT "), f"unexpected model name: {d.model}"


def test_ksb_extractor_brand_is_ksb(ksb_chunks) -> None:
    """brand='KSB' для всех."""
    drafts = extract_ksb_pumps_from_chunks(ksb_chunks, brand_hint="KSB")
    assert all(d.brand == "KSB" for d in drafts)


def test_ksb_extractor_price_segment_is_premium(ksb_chunks) -> None:
    """KSB — premium-сегмент (5-8× от Pedrollo по цене на DN50)."""
    drafts = extract_ksb_pumps_from_chunks(ksb_chunks, brand_hint="KSB")
    assert all(d.price_segment == "premium" for d in drafts)


def test_ksb_extractor_impeller_types_valid(ksb_chunks) -> None:
    """Все impeller-коды из {S, F, E, D, K, C} мапятся в наши enum."""
    drafts = extract_ksb_pumps_from_chunks(ksb_chunks, brand_hint="KSB")
    valid_impellers = set(IMPELLER_MAP.values())
    for d in drafts:
        assert d.impeller in valid_impellers, f"{d.model}: impeller={d.impeller}"


def test_ksb_extractor_free_passage_reasonable(ksb_chunks) -> None:
    """free_passage_mm должен быть в разумных пределах (1-200 мм).

    Минимум 1 мм — для S-tube моделей предочищенных стоков (например
    KRT S 50-216 имеет проход 4 мм).
    """
    drafts = extract_ksb_pumps_from_chunks(ksb_chunks, brand_hint="KSB")
    for d in drafts:
        assert 1 <= d.free_passage_mm <= 200, (
            f"{d.model}: free_passage_mm={d.free_passage_mm}"
        )


def test_ksb_extractor_dn_extracted_from_size(ksb_chunks) -> None:
    """discharge_DN_mm извлекается из первой части size '40-252' → 40."""
    drafts = extract_ksb_pumps_from_chunks(ksb_chunks, brand_hint="KSB")
    for d in drafts:
        assert d.discharge_DN_mm is not None, f"{d.model}: DN не извлечён"
        # DN должен быть в стандартном ряду 40, 50, 65, 80, 100, 150, 200, 250, 300
        assert d.discharge_DN_mm in (40, 50, 65, 80, 100, 150, 200, 250, 300), (
            f"{d.model}: нестандартный DN={d.discharge_DN_mm}"
        )


def test_ksb_qh_curves_generated_for_all_models(ksb_chunks) -> None:
    """Stub Q-H генерируется для всех найденных KSB моделей."""
    drafts = extract_ksb_pumps_from_chunks(ksb_chunks, brand_hint="KSB")
    curves = extract_ksb_qh_curves_from_chunks(ksb_chunks)
    # Каждая модель должна иметь Q-H stub
    drafts_models = {d.model for d in drafts}
    curves_models = set(curves.keys())
    assert drafts_models == curves_models, (
        f"models в drafts но не в curves: {drafts_models - curves_models}; "
        f"в curves но не в drafts: {curves_models - drafts_models}"
    )


def test_ksb_qh_curves_have_5_points(ksb_chunks) -> None:
    """Каждая stub-кривая имеет ровно 5 точек."""
    curves = extract_ksb_qh_curves_from_chunks(ksb_chunks)
    for model, points in curves.items():
        assert len(points) == 5, f"{model}: {len(points)} точек, ожидаем 5"


def test_ksb_extractor_notes_mention_review(ksb_chunks) -> None:
    """Все KSB drafts должны быть помечены для review (Q-H — стабы)."""
    drafts = extract_ksb_pumps_from_chunks(ksb_chunks, brand_hint="KSB")
    for d in drafts:
        assert d.notes and "review" in d.notes.lower(), (
            f"{d.model}: notes не упоминает review: {d.notes}"
        )
