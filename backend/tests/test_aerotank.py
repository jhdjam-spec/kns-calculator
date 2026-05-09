"""Тесты Phase 3N — расчёт аэротенка по СП 32.13330 §7.4.5."""
from __future__ import annotations

import pytest

from pump_calculator.los import (
    LOAD_PROFILES,
    calc_aerotank,
    list_load_profiles,
)


def test_4_load_profiles():
    """4 профиля нагрузки для разных стоков."""
    expected = {"domestic_low", "domestic_medium", "industrial_low", "industrial_high"}
    assert set(LOAD_PROFILES.keys()) == expected


def test_typical_household_50_users():
    """50 чел = ~10 м³/сут, БПК=300 → V ≈ 5-7 м³."""
    result = calc_aerotank(
        Q_m3_day=10,
        BOD_inlet_mg_l=300,
        profile="domestic_medium",
    )
    # V = 10 × 300 / (300 × 2.5 × 0.7) = 5.71 м³
    assert result.V_aerotank_m3 == pytest.approx(5.71, abs=0.5)
    assert 13 < result.aeration_time_h < 14


def test_industrial_high_load_larger_volume():
    """Промышл. с высокой нагрузкой → V больше."""
    result = calc_aerotank(
        Q_m3_day=10,
        BOD_inlet_mg_l=2000,
        profile="industrial_high",
    )
    # V = 10 × 2000 / (150 × 3.5 × 0.7) = 54.4 м³
    assert result.V_aerotank_m3 > 50


def test_aeration_time_scales_with_bod():
    """С увеличением БПК растёт время аэрации."""
    low = calc_aerotank(Q_m3_day=10, BOD_inlet_mg_l=200, profile="domestic_low")
    high = calc_aerotank(Q_m3_day=10, BOD_inlet_mg_l=600, profile="domestic_low")
    assert high.aeration_time_h > low.aeration_time_h


def test_air_flow_calculation():
    """Расход воздуха масштабируется с БПК × Q."""
    result = calc_aerotank(Q_m3_day=10, BOD_inlet_mg_l=300, profile="domestic_medium")
    assert result.air_flow_m3h > 0


def test_bod_removed_calculation():
    """Степень очистки = (1 - C_out/C_in)·100%."""
    result = calc_aerotank(
        Q_m3_day=10,
        BOD_inlet_mg_l=300,
        BOD_outlet_target_mg_l=15,
        profile="domestic_medium",
    )
    expected = (1 - 15/300) * 100   # 95%
    assert result.BOD_removed_pct == pytest.approx(expected, abs=0.5)


def test_invalid_profile_raises():
    """Неизвестный профиль → ValueError."""
    with pytest.raises(ValueError):
        calc_aerotank(
            Q_m3_day=10,
            BOD_inlet_mg_l=300,
            profile="ultra_extreme",  # type: ignore[arg-type]
        )


def test_references_returned():
    """Ссылки на СП 32 + ИТС НДТ."""
    result = calc_aerotank(Q_m3_day=10, BOD_inlet_mg_l=300)
    codes = [r["regulation_code"] for r in result.references]
    assert any("СП 32" in c for c in codes)
    assert any("ИТС" in c for c in codes)


def test_list_load_profiles_for_ui():
    """Каталог 4 профилей для UI."""
    profiles = list_load_profiles()
    assert len(profiles) == 4
    for p in profiles:
        assert "profile" in p
        assert "description" in p
        assert "n_mg_bod_g_day" in p


def test_sludge_age_reasonable():
    """Возраст ила в разумных пределах."""
    result = calc_aerotank(Q_m3_day=10, BOD_inlet_mg_l=300, profile="domestic_medium")
    assert 1 < result.sludge_age_days < 100
