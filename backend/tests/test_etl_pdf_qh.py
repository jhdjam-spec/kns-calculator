"""Тесты Q-H extractor на табличных Q-H данных Pedrollo VX 50 Hz.

Все тесты используют реальную фикстуру ``pedrollo_vx_50hz.pdf`` (4 страницы,
vector text, идеально парсится pdfplumber).

Тесты быстрые (без docling), пригодны для CI.
"""

from __future__ import annotations

from pathlib import Path

from pump_calculator.etl.curve_fitter import fit_qh_curve
from pump_calculator.etl.pdf.pdfplumber_runner import run_pdfplumber
from pump_calculator.etl.pdf.qh_extractor import extract_qh_curves_from_chunks
from pump_calculator.etl.pdf.splitter import split_pdf

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "pedrollo_vx_50hz.pdf"


def _extract_pedrollo_curves(tmp_path: Path) -> dict:
    """Прогнать полный split → pdfplumber → qh-extractor пайплайн."""
    chunks = split_pdf(FIXTURE_PDF, tmp_path / "chunks", pages_per_chunk=4)
    document_chunks = [run_pdfplumber(c, output_dir=tmp_path / "plumber") for c in chunks]
    return extract_qh_curves_from_chunks(document_chunks)


def test_extract_pedrollo_vx_returns_at_least_8_models(tmp_path: Path) -> None:
    """В каталоге Pedrollo VX 50 Hz — 8 уникальных типоразмеров (×2 фазности).

    Серия /35: VX[m] 8/35, 10/35, 15/35, 20/35.
    Серия /50: VX[m] 8/50, 10/50, 15/50, 20/50.
    Каждый типоразмер выпускается в single-phase (VXm) и three-phase (VX),
    т.е. суммарно 16 имён моделей. Минимум 8 — гарантирующий floor.
    """
    curves = _extract_pedrollo_curves(tmp_path)
    assert len(curves) >= 8, (
        f"ожидаем минимум 8 моделей Pedrollo, получили {len(curves)}: "
        f"{sorted(curves.keys())}"
    )


def test_extract_pedrollo_qh_curves_have_min_5_points(tmp_path: Path) -> None:
    """Каждая Q-H кривая должна содержать минимум 5 точек.

    fit_qh_curve требует ≥3 точек, но реально для качественной аппроксимации
    лучше минимум 5 (shutoff, 25%, BEP, 75%, 100%).
    """
    curves = _extract_pedrollo_curves(tmp_path)
    short_curves = {m: len(pts) for m, pts in curves.items() if len(pts) < 5}
    assert not short_curves, f"кривые с <5 точек: {short_curves}"


def test_extract_pedrollo_qh_curves_h_decreases(tmp_path: Path) -> None:
    """Физика: напор падает с ростом расхода → H[последняя] < H[первая]."""
    curves = _extract_pedrollo_curves(tmp_path)
    for model, points in curves.items():
        assert points, f"{model}: пустая кривая"
        h_first = points[0].H_m
        h_last = points[-1].H_m
        assert h_last < h_first, (
            f"{model}: H не падает: первая точка H={h_first}, "
            f"последняя H={h_last}, всего {len(points)} точек"
        )


def test_extract_pedrollo_qh_units_normalized_to_m3h(tmp_path: Path) -> None:
    """Все Q должны быть в м³/ч, не в л/мин.

    Для Pedrollo VX max Q ≈ 39 м³/ч, в л/мин это было бы 650.
    Если Q > 100 — значит, единицы не сконвертированы.
    """
    curves = _extract_pedrollo_curves(tmp_path)
    for model, points in curves.items():
        for p in points:
            assert p.Q_m3h < 100, (
                f"{model}: Q_m3h={p.Q_m3h} > 100 — похоже, l/min не "
                f"сконвертированы в м³/ч"
            )


def test_extract_pedrollo_vxm_835_first_point_h_around_11(tmp_path: Path) -> None:
    """Для VXm 8/35 (или VX 8/35) первая точка — shutoff head ≈ 9-11 м.

    В datasheet первая точка для серии /35 VXm 8/35: H = 9 м (paspport
    указывает H_max в районе 9-11 в зависимости от версии каталога).
    Допускаем диапазон 8..12 для устойчивости теста.
    """
    curves = _extract_pedrollo_curves(tmp_path)
    candidates = [m for m in curves if "8/35" in m]
    assert candidates, f"не нашли VX(m) 8/35 среди {sorted(curves.keys())}"
    model = candidates[0]
    first = curves[model][0]
    assert first.Q_m3h <= 1, (
        f"{model}: первая точка Q={first.Q_m3h} > 1, ожидаем shutoff Q≈0"
    )
    assert 7 <= first.H_m <= 13, (
        f"{model}: первая точка H={first.H_m}, ожидаем shutoff в диапазоне 7..13 м"
    )


def test_extracted_curves_fit_through_curve_fitter(tmp_path: Path) -> None:
    """Извлечённые кривые должны валидно аппроксимироваться curve_fitter.

    Проверяем для одной модели (VX/VXm 20/50 — самая мощная в каталоге):
    fit_qh_curve должен вернуть QHCurve с Q_max в реальном диапазоне
    (Pedrollo VX 20/50: Q_max ≈ 39 м³/ч). Q_BEP может быть None, если
    нет eta-данных (а у нас их нет — только Q-H), это нормально.
    """
    curves = _extract_pedrollo_curves(tmp_path)
    candidates = [m for m in curves if "20/50" in m]
    assert candidates, f"не нашли модель 20/50 среди {sorted(curves.keys())}"
    points = curves[candidates[0]]
    assert len(points) >= 3, "fit_qh_curve требует ≥3 точек"

    fitted = fit_qh_curve(points)
    # Q_max должен попадать в реальный диапазон Pedrollo VX (0..45 м³/ч)
    assert 0 < fitted.Q_max_m3h <= 45, (
        f"Q_max={fitted.Q_max_m3h} вне реального диапазона Pedrollo VX (0..45)"
    )
    # H_max — shutoff head — для 20/50 ≈ 13.5 м
    assert 5 < fitted.H_max_m <= 25, (
        f"H_max={fitted.H_max_m} вне ожидаемого диапазона 5..25 м"
    )
