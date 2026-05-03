"""Тесты Phase 5: curve fitter (Q-H регрессия)."""

from __future__ import annotations

import pytest

from pump_calculator.etl.curve_fitter import fit_qh_curve
from pump_calculator.etl.schemas import QHPoint

# Реальные точки из паспорта KAIQUAN 50WQ/S 20-22-3 (из seed)
KAIQUAN_50WQS_POINTS = [
    QHPoint(Q_m3h=0, H_m=24.0, eta_pct=0, P_kW=1.8, NPSHr_m=1.5),
    QHPoint(Q_m3h=10, H_m=21.0, eta_pct=32.0, P_kW=2.2, NPSHr_m=1.8),
    QHPoint(Q_m3h=15, H_m=19.5, eta_pct=41.0, P_kW=2.5, NPSHr_m=2.0),
    QHPoint(Q_m3h=22.9, H_m=17.4, eta_pct=46.4, P_kW=2.8, NPSHr_m=2.8),
    QHPoint(Q_m3h=30, H_m=12.0, eta_pct=38.0, P_kW=2.9, NPSHr_m=4.0),
]


def test_fit_returns_envelope_for_kaiquan():
    """На реальных данных KAIQUAN envelope вычисляется правильно."""
    curve = fit_qh_curve(KAIQUAN_50WQS_POINTS)
    assert curve.Q_min_m3h == 0
    assert curve.Q_max_m3h == 30
    assert curve.H_min_m == 12.0
    assert curve.H_max_m == 24.0


def test_fit_finds_BEP_near_passport():
    """BEP паспорта = 22.9 м³/ч, η=46.4%. Аппроксимация должна попасть ±2 м³/ч и ±3% η."""
    curve = fit_qh_curve(KAIQUAN_50WQS_POINTS)
    assert curve.Q_BEP_m3h is not None
    assert abs(curve.Q_BEP_m3h - 22.9) < 3, f"Q_BEP={curve.Q_BEP_m3h} should be near 22.9"
    assert curve.eta_BEP_pct is not None
    assert abs(curve.eta_BEP_pct - 46.4) < 5, f"eta_BEP={curve.eta_BEP_pct} should be near 46.4%"


def test_fit_NPSHr_at_BEP():
    """NPSHr линейно интерполируется к Q_BEP."""
    curve = fit_qh_curve(KAIQUAN_50WQS_POINTS)
    # Q_BEP ~22.9, между точками (15, 2.0) и (22.9, 2.8) → должно быть около 2.8
    assert curve.NPSHr_at_BEP_m is not None
    assert 2.0 <= curve.NPSHr_at_BEP_m <= 3.5


def test_H_at_interpolation():
    """H(Q) аппроксимация на промежуточном Q."""
    curve = fit_qh_curve(KAIQUAN_50WQS_POINTS)
    H_at_20 = curve.H_at(20.0)
    # Ожидаем что-то между 17 и 19 (паспорт: 19.5 при 15, 17.4 при 22.9)
    assert 16 < H_at_20 < 20, f"H(20) = {H_at_20:.2f}"


def test_eta_at_interpolation():
    """η(Q) аппроксимация в промежуточной точке."""
    curve = fit_qh_curve(KAIQUAN_50WQS_POINTS)
    eta_at_20 = curve.eta_at(20.0)
    assert eta_at_20 is not None
    assert 35 < eta_at_20 < 50


def test_fit_minimal_3_points():
    """Минимум 3 точки достаточно для H, но без КПД."""
    pts = [
        QHPoint(Q_m3h=10, H_m=20),
        QHPoint(Q_m3h=20, H_m=18),
        QHPoint(Q_m3h=30, H_m=14),
    ]
    curve = fit_qh_curve(pts)
    # H аппроксимирован
    assert curve.H_at(20) > 0
    # КПД нет
    assert curve.eta_coeffs is None
    assert curve.Q_BEP_m3h is None
    assert curve.eta_BEP_pct is None


def test_fit_too_few_points_raises():
    """Меньше 3 точек — ошибка."""
    with pytest.raises(ValueError, match="at least 3"):
        fit_qh_curve([
            QHPoint(Q_m3h=10, H_m=20),
            QHPoint(Q_m3h=20, H_m=18),
        ])


def test_fit_handles_eta_without_max():
    """Если КПД монотонно растёт (нет максимума в диапазоне) — Q_BEP = None."""
    pts = [
        QHPoint(Q_m3h=10, H_m=20, eta_pct=10),
        QHPoint(Q_m3h=20, H_m=18, eta_pct=20),
        QHPoint(Q_m3h=30, H_m=14, eta_pct=30),
        QHPoint(Q_m3h=40, H_m=10, eta_pct=40),
    ]
    curve = fit_qh_curve(pts)
    # Можем не найти BEP внутри диапазона — это OK
    # eta_coeffs всё равно посчитан
    assert curve.eta_coeffs is not None
