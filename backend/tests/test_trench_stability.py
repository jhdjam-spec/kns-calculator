"""Тесты trench_stability — устойчивость откоса траншеи.

Sub T cross-domain P2 (2026-05-13): K_p для траншеи (СП 45.13330.2017 §6.1).
Закрывает PhD-Mechanics audit backlog.

Источники проверки:
  - СП 45.13330.2017 §6.1 (cntd.ru/document/456066600)
  - СП 22.13330.2016 §5.6.2 — K_p теория Кулона
"""
from __future__ import annotations

import pytest

from pump_calculator.structural import (
    GroundContext,
    check_trench_stability,
)


def test_sand_medium_shallow_no_sheet_pile():
    """Песок ср. плотности, z=2 м, УГВ глубоко — шпунт не нужен.

    СП 45 табл. 6.1: sand_medium @ 1.5 м → 0.5:1; @ 3 м → 0.75:1.
    Линейная интерполяция при z=2 м → 0.583:1.
    """
    ctx = GroundContext(soil_type="sand_medium", groundwater_level_m=-10.0,
                        install_depth_m=2.0)
    result = check_trench_stability(ctx, depth_m=2.0)
    assert result.sheet_pile_required is False
    assert result.sheet_pile_reason is None
    # slope ∈ (0.5, 0.75): линейная интерполяция между 1.5 и 3 м
    assert 0.55 < result.safe_slope_ratio_m_per_h < 0.65
    # σ_p = 18 × 2 × K_p (3.0 для φ=30°) = 108
    assert result.passive_resistance_kPa == pytest.approx(108.0, rel=0.02)


def test_deep_trench_5m_mandates_sheet_pile():
    """z >= 5 м — шпунт обязателен по СП 45 §6.1.3 для любого грунта."""
    ctx = GroundContext(soil_type="sand_dense", groundwater_level_m=-10.0,
                        install_depth_m=5.5)
    result = check_trench_stability(ctx, depth_m=5.5)
    assert result.sheet_pile_required is True
    assert "СП 45" in (result.sheet_pile_reason or "")
    assert "5" in (result.sheet_pile_reason or "")
    # σ_p ≈ 18 × 5.5 × K_p_dense (φ=38°)
    assert result.passive_resistance_kPa > 100


def test_gwl_above_bottom_mandates_sheet_pile():
    """УГВ выше дна траншеи → шпунт обязателен (СП 45 §6.1.4)."""
    ctx = GroundContext(
        soil_type="sand_medium",
        groundwater_level_m=-1.0,  # УГВ на 1 м ниже земли
        install_depth_m=3.0,        # дно на 3 м → УГВ на 2 м выше дна
    )
    result = check_trench_stability(ctx, depth_m=3.0)
    assert result.sheet_pile_required is True
    assert "грунтовых вод" in (result.sheet_pile_reason or "").lower()


def test_peat_always_sheet_pile():
    """Торф — шпунт обязателен независимо от глубины (СП 45 §6.1.3)."""
    ctx = GroundContext(soil_type="peat", groundwater_level_m=-10.0,
                        install_depth_m=1.5)
    result = check_trench_stability(ctx, depth_m=1.5)
    assert result.sheet_pile_required is True
    assert "Торф" in (result.sheet_pile_reason or "") or \
           "торф" in (result.sheet_pile_reason or "").lower() or \
           "слаб" in (result.sheet_pile_reason or "").lower() or \
           "водонасыщ" in (result.sheet_pile_reason or "").lower()


def test_clay_hard_vertical_until_1_5m():
    """Твёрдая глина допускает вертикальный откос до 1.5 м (СП 45)."""
    ctx = GroundContext(soil_type="clay_hard", groundwater_level_m=-10.0,
                        install_depth_m=1.5)
    result = check_trench_stability(ctx, depth_m=1.5)
    assert result.sheet_pile_required is False
    # Таблица: clay_hard @ 1.5 м = 0.0 (вертикально)
    assert result.safe_slope_ratio_m_per_h == 0.0
    assert result.horizontal_clearance_m == 0.0


def test_clay_soft_deep_recommends_sheet_pile():
    """clay_soft @ z > 3 м — шпунт рекомендуется (СП 45 §6.1.2)."""
    ctx = GroundContext(soil_type="clay_soft", groundwater_level_m=-10.0,
                        install_depth_m=4.0)
    result = check_trench_stability(ctx, depth_m=4.0)
    assert result.sheet_pile_required is True
    assert "мягко" in (result.sheet_pile_reason or "").lower() or \
           "соф" in (result.sheet_pile_reason or "").lower() or \
           "слаб" in (result.sheet_pile_reason or "").lower()


def test_horizontal_clearance_grows_with_depth():
    """h_отбивки = depth × slope: глубже → больше отбивка."""
    ctx_shallow = GroundContext(soil_type="sand_medium", groundwater_level_m=-10,
                                install_depth_m=2.0)
    ctx_deep = GroundContext(soil_type="sand_medium", groundwater_level_m=-10,
                             install_depth_m=4.0)
    r_shallow = check_trench_stability(ctx_shallow, depth_m=2.0)
    r_deep = check_trench_stability(ctx_deep, depth_m=4.0)
    assert r_deep.horizontal_clearance_m > r_shallow.horizontal_clearance_m


def test_passive_resistance_grows_with_depth():
    """σ_p = γ·z·K_p — растёт линейно с глубиной."""
    ctx_2m = GroundContext(soil_type="sand_medium", groundwater_level_m=-10,
                           install_depth_m=2.0)
    ctx_4m = GroundContext(soil_type="sand_medium", groundwater_level_m=-10,
                           install_depth_m=4.0)
    r_2 = check_trench_stability(ctx_2m, depth_m=2.0)
    r_4 = check_trench_stability(ctx_4m, depth_m=4.0)
    # σ_p удваивается при удвоении z
    assert r_4.passive_resistance_kPa == pytest.approx(
        2 * r_2.passive_resistance_kPa, rel=1e-3
    )


def test_negative_depth_clamps_to_zero():
    """Защита от отрицательной глубины."""
    ctx = GroundContext(soil_type="sand_medium", install_depth_m=0.0)
    result = check_trench_stability(ctx, depth_m=-1.0)
    assert result.depth_m == 0.0
    assert result.passive_resistance_kPa == 0.0
