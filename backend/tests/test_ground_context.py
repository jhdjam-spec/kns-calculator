"""Тесты GroundContext + lateral_pressure (v0.4 2026-05-13).

Sc.D. audit cross-domain P0: единый GroundContext для soil + gwl + T.
Закрывает PhD-Mechanics audit P1-4 (K_a=0.33 hardcode) и P0-3 (УГВ).

Источники проверки:
  - СП 22.13330.2016 табл. А.1: γ, φ, K_a по типу грунта
  - Coulomb 1776: K_a = tan²(45° - φ/2)
  - Jaky 1944: K_0 = 1 - sin(φ)
  - ISO 80000-3: g = 9.80665 м/с²
"""
from __future__ import annotations

import math

import pytest

from pump_calculator.structural import (
    GAMMA_WATER_KN_M3,
    GroundContext,
    LateralPressure,
    calculate_pressure,
    check_corpus_strength,
    wall_friction_force_kN,
)

# ────────────────────────────────────────────────────────────────────────
# 1. K_a/K_p/K_0 для разных грунтов
# ────────────────────────────────────────────────────────────────────────


def test_sand_medium_phi_30_K_a_0_33():
    """Песок ср. плотности: φ=30° → K_a = tan²(30°) ≈ 0.333.

    СП 22 А.1, default — соответствует старому hardcode v0.2.
    """
    ctx = GroundContext(soil_type="sand_medium")
    assert ctx.phi_deg == 30
    assert ctx.gamma_kN_m3 == pytest.approx(18.0)
    # K_a = tan²(45-15) = tan²(30) = 1/3 = 0.333
    assert ctx.K_a == pytest.approx(1.0 / 3.0, rel=1e-3)
    # K_p = tan²(45+15) = tan²(60) = 3.0
    assert ctx.K_p == pytest.approx(3.0, rel=1e-3)
    # K_0 = 1 - sin(30) = 0.5
    assert ctx.K_0 == pytest.approx(0.5, rel=1e-3)


def test_clay_plastic_phi_15_K_a_0_59():
    """Глина пластичная: φ=15° → K_a ≈ 0.59 (по СП 22 А.1).

    Худший сценарий для прочности — в 2× выше дефолта.
    """
    ctx = GroundContext(soil_type="clay_plastic")
    assert ctx.phi_deg == 15
    # K_a = tan²(45 - 7.5) = tan²(37.5°)
    expected_K_a = math.tan(math.radians(37.5)) ** 2
    assert ctx.K_a == pytest.approx(expected_K_a, rel=1e-3)
    assert ctx.K_a == pytest.approx(0.589, rel=1e-2)


def test_peat_resistivity_low():
    """Торф: φ=10°, K_a=0.70, низкое сопротивление (10-50 Ом·м)."""
    ctx = GroundContext(soil_type="peat")
    assert ctx.gamma_kN_m3 == pytest.approx(11.0)
    assert ctx.phi_deg == 10
    # K_a = tan²(45 - 5) = tan²(40°) ≈ 0.704
    assert ctx.K_a == pytest.approx(0.704, rel=1e-2)
    # ПУЭ 1.7: торф 10-50 Ом·м (хорошее заземление, плохая прочность)
    assert ctx.resistivity_ohm_m <= 50
    assert ctx.resistivity_ohm_m >= 10


# ────────────────────────────────────────────────────────────────────────
# 2. Lateral pressure
# ────────────────────────────────────────────────────────────────────────


def test_lateral_pressure_at_5m_sand():
    """Песок sand_medium, z=5 м, УГВ глубоко → σ_a ≈ 30 кПа.

    γ·z·K_a = 18·5·(1/3) = 30 кПа.
    """
    ctx = GroundContext(soil_type="sand_medium", groundwater_level_m=-10.0)
    p = calculate_pressure(ctx, z_m=5.0)
    assert isinstance(p, LateralPressure)
    assert p.active_kPa == pytest.approx(30.0, rel=1e-2)
    # σ_p = 18·5·3 = 270
    assert p.passive_kPa == pytest.approx(270.0, rel=1e-2)
    # σ_0 = 18·5·0.5 = 45
    assert p.at_rest_kPa == pytest.approx(45.0, rel=1e-2)
    # УГВ ниже точки z=5 → σ_w = 0
    assert p.water_component_kPa == pytest.approx(0.0)
    assert p.total_active_with_water_kPa == pytest.approx(30.0, rel=1e-2)


def test_water_component_when_gwl_above_bottom():
    """УГВ -2 м (т.е. на 2 м ниже земли), z=5 м → z_w=3 м, σ_w ≈ 29.4 кПа.

    σ_x = γ·z·K_a + γ_w·z_w = 30 + 9.81·3 ≈ 59.4 кПа.
    Реальный кейс Евпатории (PhD-Mechanics P0-3).
    """
    ctx = GroundContext(soil_type="sand_medium", groundwater_level_m=-2.0)
    p = calculate_pressure(ctx, z_m=5.0)
    # σ_w = 9.80665 × (5 - 2) = 29.42 кПа
    assert p.water_component_kPa == pytest.approx(GAMMA_WATER_KN_M3 * 3.0, rel=1e-3)
    # σ_a = 30 кПа (грунт)
    assert p.active_kPa == pytest.approx(30.0, rel=1e-2)
    assert p.total_active_with_water_kPa == pytest.approx(
        30.0 + GAMMA_WATER_KN_M3 * 3.0, rel=1e-2,
    )


def test_corpus_strength_passes_at_3m():
    """Стандартный кейс: песок, z=3 м, УГВ глубоко → ПЭ100 SDR17 OK.

    σ_x = 18·3·0.33 = 18 кПа << 50 кПа → SF=2.7, passes=True.
    """
    ctx = GroundContext(
        soil_type="sand_medium",
        groundwater_level_m=-10.0,
        install_depth_m=3.0,
    )
    res = check_corpus_strength(ctx)
    assert res["passes"] is True
    assert res["needs_reinforcement"] is False
    assert res["safety_factor"] > 2.0
    assert res["recommendation"] == "PE100 SDR17 OK"
    assert res["sigma_total_kPa"] < 50.0


def test_corpus_strength_fails_at_6m_with_water():
    """Глубокий корпус z=6 м, глина пластичная, УГВ=-1 → SF<1.2.

    σ_a = 18·6·0.59 ≈ 63.7 + σ_w = 9.81·5 ≈ 49 → Σ≈113 кПа.
    Это >> 50 кПа (ПЭ100 SDR17), не проходит даже SDR11 (80 кПа).
    """
    ctx = GroundContext(
        soil_type="clay_plastic",
        groundwater_level_m=-1.0,
        install_depth_m=6.0,
    )
    res = check_corpus_strength(ctx)
    assert res["passes"] is False
    assert res["needs_reinforcement"] is True
    # >80 кПа → нужны рёбра / ж/б обойма
    assert res["sigma_total_kPa"] > 80.0
    assert "Ribs" in res["recommendation"] or "jacket" in res["recommendation"]


# ────────────────────────────────────────────────────────────────────────
# 3. GroundContext.from_l1 — backward compat
# ────────────────────────────────────────────────────────────────────────


class _MockL1:
    """Минимальный L1Input-like для теста from_l1."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_from_l1_defaults_when_none():
    """L1 без soil_type/gwl/temp → default sand_medium / gwl=-5 / T=20.

    Backward compat (Sc.D. audit P0).
    """
    ctx = GroundContext.from_l1(None)
    assert ctx.soil_type == "sand_medium"
    assert ctx.groundwater_level_m == -5.0
    assert ctx.liquid_temp_c == 20.0
    assert ctx.install_depth_m == 3.0

    # Также если L1 пустой
    l1 = _MockL1()
    ctx2 = GroundContext.from_l1(l1)
    assert ctx2.soil_type == "sand_medium"


def test_from_l1_extracts_fields():
    """L1 с заполненными полями → GroundContext с правильными значениями."""
    l1 = _MockL1(
        soil_type="clay_soft",
        groundwater_level_m=-1.5,
        liquid_temp_c=35.0,
        install_depth_inlet_mm=4500,
    )
    ctx = GroundContext.from_l1(l1)
    assert ctx.soil_type == "clay_soft"
    assert ctx.groundwater_level_m == -1.5
    assert ctx.liquid_temp_c == 35.0
    assert ctx.install_depth_m == 4.5  # 4500 мм / 1000


def test_gwl_above_bottom_geometry():
    """Геометрия: install_depth=5, gwl=-2 → УГВ на 3 м выше дна корпуса."""
    ctx = GroundContext(
        soil_type="sand_medium",
        groundwater_level_m=-2.0,
        install_depth_m=5.0,
    )
    assert ctx.gwl_above_bottom_m == pytest.approx(3.0)
    assert ctx.is_submerged is True

    # УГВ на -8 м (далеко ниже) → 0
    ctx2 = GroundContext(install_depth_m=5.0, groundwater_level_m=-8.0)
    assert ctx2.gwl_above_bottom_m == 0.0
    assert ctx2.is_submerged is False


def test_wall_friction_force_increases_with_depth():
    """F_трение = 0.4 × σ_a × A_wall (Sc.D. cross-domain P0)."""
    ctx = GroundContext(soil_type="sand_medium", install_depth_m=4.0)
    # Стенка площадью 30 м²
    F = wall_friction_force_kN(ctx, wall_area_m2=30.0)
    # z_avg=2, σ_a=18·2·0.333≈12, F=0.4·12·30=144
    assert F > 100
    assert F < 200
