"""Тесты Phase 3J — α-коэффициенты СП 30.13330.2020 §5.4."""
from __future__ import annotations

import pytest

from pump_calculator.water_supply import (
    alpha_b1,
    calc_q_max_sec_alpha,
    estimate_n_devices,
)


def test_alpha_table_endpoints():
    """Граничные точки таблицы Б.1."""
    assert alpha_b1(0.001) == pytest.approx(0.200, abs=0.001)
    assert alpha_b1(1.0) == pytest.approx(1.711, abs=0.01)
    assert alpha_b1(10.0) == pytest.approx(10.448, abs=0.01)


def test_alpha_interpolation():
    """Линейная интерполяция между точками."""
    # Между PN=0.1 (α=0.442) и PN=0.15 (α=0.535)
    # PN=0.125 → α ≈ 0.442 + (0.535-0.442) × (0.125-0.1)/(0.15-0.1) = 0.4885
    assert alpha_b1(0.125) == pytest.approx(0.4885, abs=0.01)


def test_alpha_zero_and_below():
    """PN ≤ 0 → минимум таблицы."""
    assert alpha_b1(0) == 0.200
    assert alpha_b1(-1) == 0.200


def test_alpha_extrapolation_for_large_pn():
    """Большие PN — линейная экстраполяция (~0.87 × PN)."""
    # PN=200 → α ≈ 174 (по экстраполяции 0.87 × 200)
    assert alpha_b1(200) == pytest.approx(174.0, rel=0.05)


def test_jk_50_apartments():
    """ЖК 50 квартир × 4 чел = 200 чел, 300 приборов, q_hr=10."""
    result = calc_q_max_sec_alpha(
        n_users=200,
        n_devices=300,
        q_hr_l_per_user_hour=10.0,
        q_0_lps=0.20,
    )
    # P = (10×200) / (0.20×300×3600) = 2000/216000 ≈ 0.00926
    assert result.P == pytest.approx(0.00926, abs=0.001)
    # PN ≈ 0.00926 × 300 = 2.78
    assert result.PN == pytest.approx(2.78, abs=0.05)
    # α(2.78) ≈ интерполяция между 2.5 (3.343) и 3.0 (3.852) → ~3.6
    assert 3.4 < result.alpha < 3.8
    # Q_max ≈ 5 × 0.20 × 3.6 = 3.6 л/с
    assert 3.4 < result.q_max_sec_lps < 3.9


def test_small_office():
    """Офис на 50 чел, 15 приборов (3 уборных по 5 приборов)."""
    result = calc_q_max_sec_alpha(
        n_users=50,
        n_devices=15,
        q_hr_l_per_user_hour=4.0,
        q_0_lps=0.20,
    )
    # P = (4×50) / (0.20×15×3600) = 200/10800 ≈ 0.0185
    # PN ≈ 0.278 → α ≈ 0.74 → Q ≈ 0.74
    assert 0.6 < result.q_max_sec_lps < 1.0


def test_zero_devices_raises():
    """N=0 — ValueError."""
    with pytest.raises(ValueError):
        calc_q_max_sec_alpha(n_users=10, n_devices=0, q_hr_l_per_user_hour=5)


def test_estimate_n_devices_residential():
    """Жилые с ваннами: ~1.5 прибора на жителя."""
    n = estimate_n_devices("residential_with_baths", n_users=200)
    assert n == 300


def test_estimate_n_devices_office():
    """Офис: ~0.3 прибора на сотрудника."""
    n = estimate_n_devices("office", n_users=100)
    assert n == 30


def test_estimate_n_devices_unknown():
    """Неизвестный тип — fallback 0.5."""
    n = estimate_n_devices("unknown_type", n_users=100)
    assert n == 50


def test_method_label():
    """Возвращается ссылка на метод СП 30."""
    result = calc_q_max_sec_alpha(n_users=10, n_devices=5, q_hr_l_per_user_hour=10)
    assert "СП 30" in result.method
    assert "α" in result.method
