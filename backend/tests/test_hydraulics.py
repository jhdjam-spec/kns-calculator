"""Юнит-тесты hydraulics.py."""

from __future__ import annotations

from pump_calculator.hydraulics import (
    auto_select_diameter_mm,
    calc_velocity_ms,
    compute_hydraulics,
    nu_water_at_t,
    round_up_to_standard,
    zhukovsky_shock_m,
)
from pump_calculator.schemas import L0Input, L1Input


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


def test_nu_water_at_t_default_20c():
    """Default T=20°C → классическая константа NU_WATER_20C."""
    nu = nu_water_at_t(20.0)
    assert abs(nu - 1.01e-6) < 1e-9


def test_nu_water_at_t_hot_40c_reduces_viscosity():
    """T=40°C → ν=0.66e-6 (vs 1.01e-6 при 20°C). По таблице IAPWS-IF97."""
    nu_20 = nu_water_at_t(20.0)
    nu_40 = nu_water_at_t(40.0)
    assert nu_40 < nu_20
    assert abs(nu_40 - 0.66e-6) < 0.05e-6  # ±5%


def test_nu_water_at_t_extrapolation():
    """T < 0 или T > 100 → fallback на крайние значения таблицы."""
    assert nu_water_at_t(-10.0) == 1.79e-6  # T=0 нижняя граница
    assert nu_water_at_t(150.0) == 0.30e-6  # T=100 верхняя граница


def test_compute_hydraulics_hot_stocks_lower_friction():
    """Для горячих стоков 40°C H_тр должно быть меньше чем для 20°C
    (ν меньше → Re выше → λ ниже)."""
    L0 = L0Input(Q_m3h=100, dH_m=10, L_m=500, wastewater_type="industrial")
    cold = compute_hydraulics(L0, None)  # default 20°C
    hot = compute_hydraulics(L0, L1Input(liquid_temp_c=40.0))

    assert hot.Re > cold.Re, "Re должно расти при нагреве"
    assert hot.friction_factor < cold.friction_factor, "λ должно падать при нагреве"
    assert hot.H_tr_m < cold.H_tr_m, "H_тр должно падать при нагреве"
    # Эффект ~5-10% для T=40°C при типовых L=500м
    assert (cold.H_tr_m - hot.H_tr_m) / cold.H_tr_m > 0.04


def test_compute_hydraulics_default_temp_backward_compat():
    """L1=None ИЛИ L1.liquid_temp_c=None → расчёт идентичен прежнему (T=20°C)."""
    L0 = L0Input(Q_m3h=50, dH_m=8, L_m=200, wastewater_type="domestic")
    r1 = compute_hydraulics(L0, None)
    r2 = compute_hydraulics(L0, L1Input(liquid_temp_c=None))
    r3 = compute_hydraulics(L0, L1Input(liquid_temp_c=20.0))
    assert r1.Re == r2.Re == r3.Re
    assert r1.H_tr_m == r2.H_tr_m == r3.H_tr_m
