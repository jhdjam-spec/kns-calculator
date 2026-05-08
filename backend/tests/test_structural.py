"""Тесты Phase 26 — прочностные расчёты."""
from __future__ import annotations

from pump_calculator.structural import (
    StructuralScenarioInput,
    calc_ballast_concrete,
    calc_ladder_geometry,
    calc_polymer_wall_thickness,
)

# ─── Пригруз ────────────────────────────────────────────────────────


def test_ballast_not_required_dry_soil():
    """УГВ глубоко (10 м) → пригруз не требуется."""
    inputs = StructuralScenarioInput(
        diameter_m=2.0,
        height_m=3.0,
        material="fiberglass",
        wall_thickness_mm=15,
        groundwater_depth_m=10.0,
        burial_depth_m=3.0,
    )
    result = calc_ballast_concrete(inputs)
    assert not result.is_required
    assert result.archimedes_force_kn == 0


def test_ballast_required_high_gw():
    """УГВ высокий, пустой корпус → пригруз нужен."""
    inputs = StructuralScenarioInput(
        diameter_m=2.5,
        height_m=4.0,
        material="hdpe",
        wall_thickness_mm=20,
        groundwater_depth_m=0.5,    # очень высокий УГВ
        burial_depth_m=4.0,
        fill_level_pct=10,           # почти пустой
    )
    result = calc_ballast_concrete(inputs)
    assert result.is_required
    assert result.ballast_concrete_volume_m3 > 0
    assert result.ballast_concrete_thickness_m > 0
    assert result.archimedes_force_kn > 0


def test_ballast_safety_factor():
    """Коэф. запаса 1.1 по СП 32 §6.3."""
    inputs = StructuralScenarioInput(
        diameter_m=1.5, height_m=2.0, material="hdpe",
        groundwater_depth_m=0.5, burial_depth_m=2.0, fill_level_pct=10,
    )
    result = calc_ballast_concrete(inputs)
    assert result.safety_factor == 1.1


# ─── Толщина стенки ────────────────────────────────────────────────


def test_wall_thickness_fiberglass_d2():
    """FRP D=2.0 м, стандартное заглубление → SN8, t≈14-15 мм."""
    inputs = StructuralScenarioInput(
        diameter_m=2.0, height_m=3.0, material="fiberglass",
        wall_thickness_mm=10, burial_depth_m=2.5, groundwater_depth_m=10,
    )
    result = calc_polymer_wall_thickness(inputs)
    assert result.sn_class == "SN8"
    assert result.required_thickness_mm > 0
    assert not result.is_current_sufficient   # 10 мм мало


def test_wall_thickness_hdpe_thicker_than_fiberglass():
    """ПЭ при том же D требует большей толщины чем FRP."""
    inp_frp = StructuralScenarioInput(
        diameter_m=2.0, height_m=3, material="fiberglass",
        wall_thickness_mm=10, burial_depth_m=2.5, groundwater_depth_m=10,
    )
    inp_hdpe = StructuralScenarioInput(
        diameter_m=2.0, height_m=3, material="hdpe",
        wall_thickness_mm=10, burial_depth_m=2.5, groundwater_depth_m=10,
    )
    r_frp = calc_polymer_wall_thickness(inp_frp)
    r_hdpe = calc_polymer_wall_thickness(inp_hdpe)
    assert r_hdpe.required_thickness_mm > r_frp.required_thickness_mm


def test_wall_thickness_concrete_skipped():
    """Бетон/сталь — отдельная методика, эта функция возвращает заглушку."""
    inputs = StructuralScenarioInput(
        diameter_m=2.0, height_m=3, material="concrete",
        wall_thickness_mm=150, burial_depth_m=2.5, groundwater_depth_m=10,
    )
    result = calc_polymer_wall_thickness(inputs)
    assert result.sn_class == "N/A"


# ─── Лестницы ──────────────────────────────────────────────────────


def test_ladder_short_no_landings():
    """H ≤ 3 м — площадки не нужны."""
    result = calc_ladder_geometry(height_m=2.5, pit_diameter_m=1.5)
    assert result.n_landings == 0


def test_ladder_medium_one_landing():
    """H=4 м — 1 промежуточная площадка."""
    result = calc_ladder_geometry(height_m=4.0, pit_diameter_m=2.0)
    assert result.n_landings == 1


def test_ladder_deep_multiple_landings():
    """H=10 м — 3 площадки (через 3 м)."""
    result = calc_ladder_geometry(height_m=10.0, pit_diameter_m=2.5)
    assert result.n_landings == 3


def test_ladder_corrosive_uses_aisi():
    """Канализация → AISI 304/316."""
    result = calc_ladder_geometry(height_m=3.0, pit_diameter_m=2.0, is_corrosive_environment=True)
    assert "AISI" in result.material


def test_ladder_handrail_height():
    """Высота поручня 1.1 м (СП 12-104)."""
    result = calc_ladder_geometry(height_m=4.0, pit_diameter_m=2.0)
    assert result.handrail_height_m == 1.1


def test_ladder_narrow_pit_warning():
    """Узкий приямок D<1.5 при H>3 — предупреждение."""
    result = calc_ladder_geometry(height_m=5.0, pit_diameter_m=1.0)
    assert any("узк" in n.lower() for n in result.notes)
