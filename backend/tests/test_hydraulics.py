"""Юнит-тесты hydraulics.py."""

from __future__ import annotations

from pump_calculator.hydraulics import (
    auto_select_diameter_mm,
    calc_velocity_ms,
    compute_hydraulics,
    round_up_to_standard,
    zhukovsky_shock_m,
)
from pump_calculator.schemas import L0Input


def test_round_up_to_standard():
    ladder = [50, 63, 75, 90, 110, 125]
    assert round_up_to_standard(50, ladder) == 50
    assert round_up_to_standard(70, ladder) == 75
    assert round_up_to_standard(110.0, ladder) == 110
    assert round_up_to_standard(200, ladder) == 125  # больше максимума → последний


def test_auto_diameter_for_typical_kns():
    """Для Q=21.2 м³/ч с v_target=1.2 → расчётный D≈79 мм → округление до 90 мм.
    Но §15.9 (СП 32 §5.4): на D=90 скорость v=0.93 м/с < v_min=1.0 для
    бытовой канализации → опускаемся до 75 мм, где v=1.33 м/с (риск
    заиливания убран).
    """
    D = auto_select_diameter_mm(21.2)
    assert D == 75
    assert calc_velocity_ms(21.2, D) >= 1.0


def test_velocity_calculation():
    """v = 4·Q / (π·D²)."""
    v = calc_velocity_ms(21.2, 90)  # м³/ч и мм
    # 21.2 м³/ч = 0.005889 м³/с; D=0.090 м; v = 4·0.005889 / (π·0.0081) = 0.926
    assert abs(v - 0.926) < 0.01


def test_compute_hydraulics_no_trass():
    """L=0 — H_тр = 0, есть только H_м и dH."""
    result = compute_hydraulics(L0Input(Q_m3h=21.2, dH_m=10.0, L_m=0.0, wastewater_type="domestic"))
    assert result.H_tr_m == 0.0
    assert result.H_m_m > 0
    assert 10 < result.H_full_m < 13


def test_compute_hydraulics_long_trass():
    """L=2000 м — H_тр должен быть значимым."""
    result = compute_hydraulics(L0Input(Q_m3h=21.2, dH_m=10.0, L_m=2000.0, wastewater_type="domestic"))
    assert result.H_tr_m > 1.0  # реально 5-15 м для длинной трассы
    assert result.safety_factor == 0.15  # для L>1000 м


def test_zhukovsky_shock_pe100():
    """Жуковский для ПЭ100 при v=1.5 м/с — ΔH ≈ 320·1.5/9.81 ≈ 49 м."""
    delta_H = zhukovsky_shock_m(1.5, "pe100_sdr17")
    assert 45 < delta_H < 55


def test_zhukovsky_shock_steel():
    """Сталь имеет высокую a → больший гидроудар: 1150·1.5/9.81 ≈ 176 м."""
    delta_H = zhukovsky_shock_m(1.5, "steel_seamless_new")
    assert 170 < delta_H < 185
