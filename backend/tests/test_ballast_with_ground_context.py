"""Тесты ballast.py rewire под GroundContext (Sub T cross-domain P2, 2026-05-13).

Backward compat:
  • calc_ballast_concrete(inputs)         — старое поведение, тесты в test_structural
  • calc_ballast_concrete(inputs, ground) — новое: γ/φ/K_a из GroundContext

Источники:
  • СП 22.13330.2016 табл. А.1 — γ, φ по типу грунта
  • СП 32.13330.2018 §6.3 — K_safety пригруза
"""
from __future__ import annotations

from pump_calculator.structural import (
    GroundContext,
    StructuralScenarioInput,
    calc_ballast_concrete,
)


def _base_inputs(**overrides) -> StructuralScenarioInput:
    """Базовый инпут — высокий УГВ, чтобы пригруз потребовался."""
    defaults = dict(
        diameter_m=2.5,
        height_m=4.0,
        material="hdpe",
        wall_thickness_mm=20,
        groundwater_depth_m=0.5,  # очень высокий УГВ
        burial_depth_m=4.0,
        fill_level_pct=10,
    )
    defaults.update(overrides)
    return StructuralScenarioInput(**defaults)


def test_ground_none_matches_legacy():
    """ground=None → identical к старому вызову (backward compat).

    Старый ballast_required_high_gw тест должен продолжать работать.
    """
    inputs = _base_inputs()
    r_legacy = calc_ballast_concrete(inputs)  # без ground
    r_explicit = calc_ballast_concrete(inputs, ground=None)
    assert r_legacy.archimedes_force_kn == r_explicit.archimedes_force_kn
    assert r_legacy.friction_resistance_kn == r_explicit.friction_resistance_kn
    assert r_legacy.ballast_concrete_volume_m3 == r_explicit.ballast_concrete_volume_m3


def test_ground_clay_plastic_increases_friction():
    """Глина пластичная (K_a=0.59) даёт большее F_трения чем песок (K_a=0.33).

    F_тр ∝ K_a · γ · tan(φ) — глина: K_a выше, γ ≈ песок, но tan(φ) ниже.
    Зависимость нелинейная — проверяем только, что значения разные
    (НЕ hardcode из inputs).
    """
    inputs = _base_inputs()
    ground_sand = GroundContext(soil_type="sand_medium",
                                groundwater_level_m=-0.5,
                                install_depth_m=4.0)
    ground_clay = GroundContext(soil_type="clay_plastic",
                                groundwater_level_m=-0.5,
                                install_depth_m=4.0)
    r_sand = calc_ballast_concrete(inputs, ground=ground_sand)
    r_clay = calc_ballast_concrete(inputs, ground=ground_clay)
    # Различные F_трения, потому что разные K_a/φ
    assert r_sand.friction_resistance_kn != r_clay.friction_resistance_kn


def test_ground_overrides_inputs_soil_fields():
    """ground задан → inputs.soil_friction_angle_deg игнорируется."""
    # inputs.phi = 30°, ground.phi = 22° (loam)
    inputs = _base_inputs(soil_friction_angle_deg=30,
                          soil_density_kg_m3=1800)
    ground_loam = GroundContext(soil_type="loam",
                                groundwater_level_m=-0.5,
                                install_depth_m=4.0)
    r_with_ground = calc_ballast_concrete(inputs, ground=ground_loam)
    r_no_ground = calc_ballast_concrete(inputs, ground=None)
    # Разные F_трения (loam.φ=22, inputs.φ=30 → разный tan)
    assert r_with_ground.friction_resistance_kn != \
           r_no_ground.friction_resistance_kn
    # Note должна указать источник GroundContext
    assert any("GroundContext" in n for n in r_with_ground.notes)
    assert any("legacy" in n.lower() for n in r_no_ground.notes)


def test_ground_peat_low_friction():
    """Торф (γ=11, φ=10°) даёт минимальное трение → больше пригруза."""
    inputs = _base_inputs()
    ground_peat = GroundContext(soil_type="peat",
                                groundwater_level_m=-0.5,
                                install_depth_m=4.0)
    ground_sand = GroundContext(soil_type="sand_dense",
                                groundwater_level_m=-0.5,
                                install_depth_m=4.0)
    r_peat = calc_ballast_concrete(inputs, ground=ground_peat)
    r_sand = calc_ballast_concrete(inputs, ground=ground_sand)
    # F_трения для торфа < песка
    assert r_peat.friction_resistance_kn < r_sand.friction_resistance_kn
    # → больше бетона нужно
    assert r_peat.ballast_concrete_volume_m3 >= r_sand.ballast_concrete_volume_m3


def test_ballast_dry_soil_not_required_with_ground():
    """ground с УГВ=-10 → пригруз не нужен (как в старом тесте)."""
    inputs = _base_inputs(groundwater_depth_m=10.0)
    ground_dry = GroundContext(soil_type="sand_medium",
                               groundwater_level_m=-10.0,
                               install_depth_m=4.0)
    r = calc_ballast_concrete(inputs, ground=ground_dry)
    assert not r.is_required
    assert r.archimedes_force_kn == 0


def test_ground_passed_keeps_safety_factor():
    """Безопасность K=1.1 сохраняется (СП 32 §6.3 legacy)."""
    inputs = _base_inputs()
    ground = GroundContext(soil_type="sand_medium",
                           groundwater_level_m=-0.5,
                           install_depth_m=4.0)
    r = calc_ballast_concrete(inputs, ground=ground)
    assert r.safety_factor == 1.1
