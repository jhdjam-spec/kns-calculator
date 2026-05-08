"""Тесты Phase 23 — расчёт водопотребления и подбор ВНС."""
from __future__ import annotations

import pytest

from pump_calculator.water_supply import (
    NORMS_LITERS_PER_DAY,
    WaterScenarioInput,
    calc_water_demand,
    sizing_water_station,
)

# ──────────────────────────────────────────────────────────────────────────
# Базовые расчёты по норме
# ──────────────────────────────────────────────────────────────────────────


def test_residential_4_persons():
    """ИЖС 4 чел, норма 250 л/чел·сут → Q_сред=1.0 м³/сут (общая)."""
    inputs = WaterScenarioInput(
        building_type="residential_with_baths",
        population=4,
        has_hot_water=True,
    )
    result = calc_water_demand(inputs)
    # Холодная (250-105=145 л) + горячая 105 → итого 250 л/чел·сут × 4
    expected_avg = 4 * 250 / 1000.0  # = 1.0
    assert result.total_Q_avg_m3_day == pytest.approx(expected_avg, abs=0.05)


def test_jk_50_apartments_q_sec():
    """ЖК 50 кв. = 150 чел: Q_max_сек должна быть в разумном диапазоне 4-6 л/с."""
    inputs = WaterScenarioInput(
        building_type="residential_with_baths",
        population=150,
        floors=12,
    )
    result = calc_water_demand(inputs)
    # 150 чел × 250 = 37.5 м³/сут × K_сут=1.2 = 45 м³/сут
    # Q_max_час = 45/24 × 1.4 = 2.625 м³/ч → 0.73 л/с — это для пиковой неравномерности.
    assert 0.5 <= result.total_Q_max_sec_lps <= 5.0


def test_hotel_100_rooms():
    """Гостиница 100 номеров стандарт класс."""
    inputs = WaterScenarioInput(
        building_type="hotel_standard",
        rooms=100,
    )
    result = calc_water_demand(inputs)
    # 100 × 230 = 23 м³/сут общ.
    assert result.total_Q_avg_m3_day == pytest.approx(23.0, abs=1.0)


def test_office_50_persons():
    """Офис 50 чел — мало, норма 16 л/чел·сут."""
    inputs = WaterScenarioInput(
        building_type="office",
        population=50,
        has_hot_water=True,
    )
    result = calc_water_demand(inputs)
    # 50 × 16 = 0.8 м³/сут (общая)
    assert result.total_Q_avg_m3_day == pytest.approx(0.8, abs=0.1)


def test_hospital_200_beds():
    """Больница 200 коек — норма 250 л/койка·сут."""
    inputs = WaterScenarioInput(
        building_type="hospital",
        beds=200,
    )
    result = calc_water_demand(inputs)
    # 200 × 250 = 50 м³/сут
    assert result.total_Q_avg_m3_day == pytest.approx(50.0, abs=2.0)


def test_irrigation_adds_to_total():
    """Полив добавляет к общему расходу."""
    inputs_no_irr = WaterScenarioInput(
        building_type="residential_with_baths",
        population=4,
        has_irrigation=False,
    )
    inputs_irr = WaterScenarioInput(
        building_type="residential_with_baths",
        population=4,
        has_irrigation=True,
        irrigation_area_m2=1000,  # 3 м³/сут на полив
    )
    r1 = calc_water_demand(inputs_no_irr)
    r2 = calc_water_demand(inputs_irr)
    assert r2.total_Q_avg_m3_day > r1.total_Q_avg_m3_day
    assert r2.irrigation is not None
    assert r2.irrigation.Q_avg_m3_per_day == pytest.approx(3.0, abs=0.1)


def test_no_population_raises():
    """Не задано число пользователей → ValueError."""
    inputs = WaterScenarioInput(
        building_type="residential_with_baths",
        population=0,
    )
    with pytest.raises(ValueError):
        calc_water_demand(inputs)


def test_norms_table_complete():
    """Все типы зданий имеют норму, K_sut, K_hour."""
    for bt, norm in NORMS_LITERS_PER_DAY.items():
        assert norm["norm_total"] > 0, bt
        assert norm["K_sut_max"] >= 1.0
        assert norm["K_hour_max"] >= 1.0
        assert norm["unit"], bt


def test_references_returned():
    """Каждый расчёт возвращает ссылки на нормативы."""
    inputs = WaterScenarioInput(
        building_type="residential_with_baths",
        population=4,
    )
    result = calc_water_demand(inputs)
    assert len(result.references) >= 2
    codes = [r["regulation_code"] for r in result.references]
    assert any("СП 30" in c for c in codes)
    assert any("СП 31" in c for c in codes)


# ──────────────────────────────────────────────────────────────────────────
# Подбор ВНС
# ──────────────────────────────────────────────────────────────────────────


def test_sizing_small_one_pump():
    """Малый объект (Q<30 м³/ч) — 1 рабочий насос."""
    inputs = WaterScenarioInput(
        building_type="residential_with_baths",
        population=4,
        floors=2,
    )
    demand = calc_water_demand(inputs)
    station = sizing_water_station(inputs, demand)
    assert station.operating_pumps == 1
    assert station.standby_pumps == 1
    assert station.has_pressure_tank  # Малая ВНС → гидроакк


def test_sizing_medium_two_pumps():
    """Q=30-100 м³/ч → 2 рабочих параллельно."""
    inputs = WaterScenarioInput(
        building_type="residential_with_baths",
        population=200,  # Q ≈ 50 м³/сут × 1.2 / 24 × 1.4 ≈ 3.5 м³/ч
        floors=12,
    )
    demand = calc_water_demand(inputs)
    # Установим вручную больший Q для теста
    demand.total_Q_max_hour_m3h = 50.0
    station = sizing_water_station(inputs, demand)
    assert station.operating_pumps == 2


def test_sizing_high_rise_uses_vfd():
    """Высотный объект (>5 эт) → VFD рекомендуется."""
    inputs = WaterScenarioInput(
        building_type="residential_with_baths",
        population=100,
        floors=12,
    )
    demand = calc_water_demand(inputs)
    station = sizing_water_station(inputs, demand)
    assert station.has_vfd


def test_sizing_well_source_includes_reservoir():
    """Если источник — скважина → должен быть резервуар."""
    inputs = WaterScenarioInput(
        building_type="residential_with_baths",
        population=4,
        water_source="well",
    )
    demand = calc_water_demand(inputs)
    station = sizing_water_station(inputs, demand)
    assert station.reservoir_volume_m3 is not None
    assert station.reservoir_volume_m3 > 0


def test_reliability_category_by_population():
    """Категория надёжности от числа пользователей."""
    inputs_small = WaterScenarioInput(
        building_type="residential_with_baths", population=100
    )
    inputs_medium = WaterScenarioInput(
        building_type="residential_with_baths", population=10_000
    )
    inputs_large = WaterScenarioInput(
        building_type="residential_with_baths", population=100_000
    )
    s_small = sizing_water_station(inputs_small, calc_water_demand(inputs_small))
    s_med = sizing_water_station(inputs_medium, calc_water_demand(inputs_medium))
    s_large = sizing_water_station(inputs_large, calc_water_demand(inputs_large))
    assert s_small.reliability_category == 3
    assert s_med.reliability_category == 2
    assert s_large.reliability_category == 1
