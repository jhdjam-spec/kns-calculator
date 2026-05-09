"""Тесты Phase 3I — расчёт спринклерных установок по СП 485.1311500.2020."""
from __future__ import annotations

import pytest

from pump_calculator.fire_water import (
    SPRINKLER_GROUPS,
    calc_sprinkler_demand,
    list_sprinkler_groups,
)


def test_8_groups_in_catalog():
    """Каталог содержит 8 групп помещений (1, 2, 3, 4.1, 4.2, 5, 6, 7)."""
    assert len(SPRINKLER_GROUPS) == 8
    expected = {"1", "2", "3", "4.1", "4.2", "5", "6", "7"}
    assert set(SPRINKLER_GROUPS.keys()) == expected


def test_group_1_office_low_load():
    """Группа 1 — офис: q_уд=0.08 л/с/м², A=60 м² → Q=4.8 л/с."""
    result = calc_sprinkler_demand(group="1")
    assert result.q_total_lps == pytest.approx(4.8, abs=0.01)
    assert result.area_m2 == 60
    assert result.duration_min == 30


def test_group_2_apartments_medium_load():
    """Группа 2 — жилые/гостиницы: q_уд=0.12 л/с/м², A=120 м² → Q=14.4 л/с."""
    result = calc_sprinkler_demand(group="2")
    assert result.q_total_lps == pytest.approx(14.4, abs=0.01)
    assert result.duration_min == 60


def test_group_4_2_high_load_industry():
    """Группа 4.2 — высокая пром. нагрузка: q_уд=0.40, A=240 → Q=96 л/с."""
    result = calc_sprinkler_demand(group="4.2")
    assert result.q_total_lps == pytest.approx(96.0, abs=0.01)
    assert result.duration_min == 90


def test_group_7_high_warehouse():
    """Группа 7 — высокий склад: q_уд=0.40, A=360 → Q=144 л/с."""
    result = calc_sprinkler_demand(group="7")
    assert result.q_total_lps == pytest.approx(144.0, abs=0.01)
    assert result.area_m2 == 360
    assert result.min_pressure_m == 25


def test_actual_area_smaller_than_calc():
    """Если реальная площадь меньше расчётной — берём фактическую (≥60)."""
    # Группа 4.1: расчётная 240, но реальное помещение 100 м²
    result = calc_sprinkler_demand(group="4.1", coverage_area_m2=100)
    assert result.area_m2 == 100
    # Расход = 0.30 × 100 = 30 л/с
    assert result.q_total_lps == pytest.approx(30.0, abs=0.01)


def test_actual_area_below_minimum():
    """Реальная 30 м² → клампится до 60 м² минимум."""
    result = calc_sprinkler_demand(group="2", coverage_area_m2=30)
    assert result.area_m2 == 60


def test_water_volume_calculation():
    """Запас воды: Q × T_сек / 1000 = м³."""
    result = calc_sprinkler_demand(group="2")
    # Q=14.4 л/с, T=60 мин → V = 14.4 × 60×60 / 1000 = 51.84 м³
    assert result.water_volume_m3 == pytest.approx(51.84, abs=0.1)


def test_invalid_group_raises():
    """Неизвестная группа → ValueError."""
    with pytest.raises(ValueError):
        calc_sprinkler_demand(group="99")  # type: ignore[arg-type]


def test_references_returned():
    """Каждый расчёт возвращает ссылки на СП 485."""
    result = calc_sprinkler_demand(group="3")
    codes = [r["regulation_code"] for r in result.references]
    assert all("СП 485" in c for c in codes)


def test_list_sprinkler_groups_for_ui():
    """list_sprinkler_groups возвращает 8 элементов для UI."""
    groups = list_sprinkler_groups()
    assert len(groups) == 8
    for g in groups:
        assert "group" in g
        assert "title" in g
        assert "examples" in g
        assert "q_uds_lps_m2" in g


def test_n_sprinklers_min_makes_sense():
    """Число оросителей: для группы 1-2 интервал 4 м (12 м²/ороситель), 3+ — 9 м²."""
    g1 = calc_sprinkler_demand(group="1")    # A=60, 12 м²/ор → ≥6
    g4 = calc_sprinkler_demand(group="4.1")  # A=240, 9 м²/ор → ≥27
    assert g1.n_sprinklers_min >= 5
    assert g4.n_sprinklers_min >= 25
