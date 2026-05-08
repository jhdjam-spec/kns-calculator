"""Тесты Phase 22 — углублённая физика."""
from __future__ import annotations

import pytest

from pump_calculator.physics_advanced import (
    PIPE_ROUGHNESS_MM,
    WAVE_CELERITY_MPS,
    atmospheric_pressure_kpa,
    darcy_friction_factor,
    darcy_weisbach_head_loss_m,
    density_wastewater_kg_m3,
    gravity_at_latitude,
    npsha_with_corrections,
    parallel_pumps_qh,
    reynolds_number,
    viscosity_wastewater_factor,
    water_hammer,
)

# ──────────────────────────────────────────────────────────────────────────
# Атмосферное давление и гравитация
# ──────────────────────────────────────────────────────────────────────────


def test_atm_pressure_sea_level():
    """На уровне моря P ≈ 101.325 кПа."""
    p = atmospheric_pressure_kpa(0, 15.0)
    assert p == pytest.approx(101.325, abs=0.5)


def test_atm_pressure_decreases_with_altitude():
    """С высотой P уменьшается."""
    p_0 = atmospheric_pressure_kpa(0)
    p_500 = atmospheric_pressure_kpa(500)
    p_1500 = atmospheric_pressure_kpa(1500)
    p_2500 = atmospheric_pressure_kpa(2500)
    assert p_500 < p_0
    assert p_1500 < p_500
    assert p_2500 < p_1500
    # Каждые 100 м ~ -1 кПа на высотах до 2-3 км
    assert (p_0 - p_2500) > 20  # на 2500 м падает >20 кПа


def test_atm_pressure_invalid_altitude():
    """Высоты вне 0-11000 м — ValueError."""
    with pytest.raises(ValueError):
        atmospheric_pressure_kpa(15000)


def test_gravity_at_equator_and_pole():
    """g на экваторе ~9.78, на полюсе ~9.83."""
    g_eq = gravity_at_latitude(0, 0)
    g_pole = gravity_at_latitude(90, 0)
    assert 9.77 < g_eq < 9.79
    assert 9.82 < g_pole < 9.84


def test_gravity_decreases_with_altitude():
    """С высотой g немного уменьшается."""
    g_0 = gravity_at_latitude(55, 0)
    g_5km = gravity_at_latitude(55, 5000)
    assert g_5km < g_0
    assert (g_0 - g_5km) == pytest.approx(0.0154, abs=0.005)


def test_npsha_with_altitude_correction():
    """NPSHa уменьшается с высотой над уровнем моря."""
    npsha_sea, _ = npsha_with_corrections(H_suction_m=2.0, altitude_m=0)
    npsha_mountain, _ = npsha_with_corrections(H_suction_m=2.0, altitude_m=2000)
    assert npsha_mountain < npsha_sea
    # Каждые 100 м высоты ~-1 м водяного столба
    assert (npsha_sea - npsha_mountain) == pytest.approx(2.0, abs=0.5)


# ──────────────────────────────────────────────────────────────────────────
# Гидроудар
# ──────────────────────────────────────────────────────────────────────────


def test_water_hammer_zhukovsky_steel():
    """Стальная труба, c≈1340 м/с, v=2 м/с → Δp ≈ ρ·c·v = 1000·1340·2 = 2.68 МПа."""
    result = water_hammer(v_ms=2.0, pipe_material="steel", pipe_length_m=10, closure_time_s=0.001)
    assert result.is_direct
    assert result.delta_p_kpa == pytest.approx(2680, rel=0.05)
    assert result.delta_h_m == pytest.approx(273, rel=0.05)


def test_water_hammer_pe100_lower_pressure():
    """ПЭ100 c≈320 м/с → давление в 4 раза меньше чем сталь."""
    r_steel = water_hammer(v_ms=2.0, pipe_material="steel", pipe_length_m=10, closure_time_s=0.001)
    r_pe = water_hammer(v_ms=2.0, pipe_material="pe100_sdr17", pipe_length_m=10, closure_time_s=0.001)
    assert r_pe.delta_p_kpa < r_steel.delta_p_kpa / 3


def test_water_hammer_slow_closure_lower():
    """Медленное закрытие → Михайлов, удар меньше."""
    r_fast = water_hammer(v_ms=2.0, pipe_material="steel", pipe_length_m=100, closure_time_s=0.05)
    r_slow = water_hammer(v_ms=2.0, pipe_material="steel", pipe_length_m=100, closure_time_s=10.0)
    # T_phase = 2·100/1340 = 0.149 c. fast(0.05)<phase, slow(10)>phase
    assert r_fast.is_direct
    assert not r_slow.is_direct
    assert r_slow.delta_p_kpa < r_fast.delta_p_kpa


def test_water_hammer_pn_classification():
    """При большом Δp — выбирается труба более высокого класса."""
    result = water_hammer(v_ms=3.0, pipe_material="steel", pipe_length_m=10, closure_time_s=0.001)
    assert result.pressure_class_required.startswith("PN")


def test_wave_celerity_table_complete():
    """Все основные материалы есть в таблице."""
    for mat in ("steel", "pe100_sdr17", "concrete", "pvc", "fiberglass"):
        assert mat in WAVE_CELERITY_MPS
        assert WAVE_CELERITY_MPS[mat] > 0


# ──────────────────────────────────────────────────────────────────────────
# Шероховатость и трение
# ──────────────────────────────────────────────────────────────────────────


def test_reynolds_number():
    """Re = v·D/ν. v=1 м/с, D=100 мм, ν=1.004e-6 → Re ≈ 99600."""
    Re = reynolds_number(v_ms=1.0, D_mm=100, T_celsius=20)
    assert 95_000 < Re < 105_000


def test_darcy_friction_laminar():
    """При Re<2300 — λ=64/Re."""
    lam = darcy_friction_factor(Re=1000, eps_over_D=0.001)
    assert lam == pytest.approx(0.064, abs=0.001)


def test_darcy_friction_turbulent():
    """При Re=10⁵ и ε/D=0.0001 — λ ≈ 0.018-0.022."""
    lam = darcy_friction_factor(Re=100_000, eps_over_D=0.0001)
    assert 0.015 < lam < 0.025


def test_darcy_weisbach_head_loss():
    """Потери Дарси-Вейсбаха для типового случая."""
    h_f, details = darcy_weisbach_head_loss_m(
        L_m=100, D_mm=100, v_ms=1.5, pipe_material="pe100"
    )
    assert h_f > 0
    assert details["regime"] == "turbulent"
    assert details["Re"] > 4000
    assert "lambda" in details


def test_pipe_roughness_table_complete():
    """Все основные материалы труб."""
    for mat in ("steel_new", "pe100", "concrete", "pvc", "fiberglass"):
        assert mat in PIPE_ROUGHNESS_MM


# ──────────────────────────────────────────────────────────────────────────
# Параллельные насосы
# ──────────────────────────────────────────────────────────────────────────


def test_parallel_pumps_increases_flow():
    """2 насоса параллельно — Q_total больше чем 1 насос."""
    # Простой полином H = 30 - 0.01·Q² (нач. напор 30 м, BEP при Q=20)
    coeffs = [30, 0, -0.01]
    single = parallel_pumps_qh(coeffs, n_pumps=1, system_static_h_m=10, system_friction_factor_per_q2=0.005)
    double = parallel_pumps_qh(coeffs, n_pumps=2, system_static_h_m=10, system_friction_factor_per_q2=0.005)
    assert double.Q_total_m3h > single.Q_total_m3h
    # Но не вдвое — характеристика системы крутая
    assert double.Q_total_m3h < 2 * single.Q_total_m3h


def test_parallel_pumps_efficiency_in_range():
    """Эффективность параллели обычно 60-95%."""
    coeffs = [30, 0, -0.01]
    result = parallel_pumps_qh(coeffs, n_pumps=2, system_static_h_m=5, system_friction_factor_per_q2=0.001)
    assert 50 <= result.flow_efficiency_pct <= 100


# ──────────────────────────────────────────────────────────────────────────
# Грязная вода
# ──────────────────────────────────────────────────────────────────────────


def test_density_increases_with_solids():
    """С увеличением содержания твёрдых ρ растёт."""
    rho_clean = density_wastewater_kg_m3(15.0, 0, 0)
    rho_dirty = density_wastewater_kg_m3(15.0, 50_000, 30_000)  # фильтрат ТКО
    assert rho_dirty > rho_clean
    assert rho_dirty > 1040  # типовой фильтрат ТКО ρ ≈ 1080-1100


def test_viscosity_factor_pure_water():
    """Чистая вода — фактор 1.0."""
    f = viscosity_wastewater_factor(0, 0)
    assert f == pytest.approx(1.0, abs=0.001)


def test_viscosity_factor_increases_with_fibers():
    """Волокна увеличивают вязкость."""
    f_clean = viscosity_wastewater_factor(0, 0)
    f_fibers = viscosity_wastewater_factor(0, 5)
    assert f_fibers > f_clean
