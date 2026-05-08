"""Тесты Phase 22 — расчёт противопожарного водоснабжения по СП 8/10.13130."""
from __future__ import annotations

import pytest

from pump_calculator.fire_water import (
    FireScenarioInput,
    calc_external_demand,
    calc_internal_demand,
    calculate_fire_scenario,
)

# ──────────────────────────────────────────────────────────────────────────
# Тесты табл. 1 СП 8.13130 — наружное пожаротушение жилых/общественных
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "occupancy,volume_m3,expected_lps",
    [
        ("residential", 500, 5.0),       # V≤1000 → 5 л/с
        ("residential", 4000, 10.0),     # V≤5000 → 10 л/с
        ("residential", 20_000, 15.0),   # V≤25000 → 15 л/с
        ("residential", 45_000, 20.0),   # V≤50000 → 20 л/с
        ("public", 100_000, 25.0),       # V≤150000
        ("public", 800_000, 30.0),       # V≤1000000
    ],
)
def test_external_demand_residential_public(occupancy, volume_m3, expected_lps):
    """СП 8.13130 табл. 1 — расход для жилых/общественных."""
    inputs = FireScenarioInput(
        occupancy=occupancy,
        building_class="I",
        volume_m3=volume_m3,
    )
    q, ref, notes = calc_external_demand(inputs)
    assert q == pytest.approx(expected_lps, abs=0.1), \
        f"{occupancy} V={volume_m3}: ожид {expected_lps}, факт {q}"
    assert "СП 8.13130.2020 табл. 1" in ref


@pytest.mark.parametrize(
    "occupancy,volume_m3,expected_lps",
    [
        ("industrial_a", 2000, 10.0),
        ("industrial_a", 4000, 15.0),
        ("industrial_b", 30_000, 20.0),
        ("industrial_d", 100_000, 20.0),  # Д кат. — V≤200000
        ("warehouse", 30_000, 20.0),       # склад
        ("garage", 30_000, 20.0),          # гараж V≤50000
    ],
)
def test_external_demand_industrial(occupancy, volume_m3, expected_lps):
    """СП 8.13130 табл. 2 — производственные/склад/гараж."""
    inputs = FireScenarioInput(
        occupancy=occupancy,
        building_class="I",
        volume_m3=volume_m3,
    )
    q, ref, notes = calc_external_demand(inputs)
    assert q == pytest.approx(expected_lps, abs=0.1), \
        f"{occupancy} V={volume_m3}: ожид {expected_lps}, факт {q}"
    assert "СП 8.13130.2020 табл. 2" in ref


def test_external_demand_class_iv_increases_flow():
    """Степень огнестойкости IV даёт K=1.25 → расход на 25% выше."""
    inputs_I = FireScenarioInput(occupancy="residential", building_class="I", volume_m3=4000)
    inputs_IV = FireScenarioInput(occupancy="residential", building_class="IV", volume_m3=4000)
    q_I, _, _ = calc_external_demand(inputs_I)
    q_IV, _, _ = calc_external_demand(inputs_IV)
    assert q_IV == pytest.approx(q_I * 1.25, rel=0.01)


# ──────────────────────────────────────────────────────────────────────────
# Тесты внутреннего ППВ
# ──────────────────────────────────────────────────────────────────────────


def test_internal_demand_low_residence_not_required():
    """5-этажный жилой дом — ВПВ не требуется."""
    inputs = FireScenarioInput(
        occupancy="residential",
        floors=5,
        volume_m3=3000,
    )
    q, notes = calc_internal_demand(inputs)
    assert q == 0.0
    assert any("не требуется" in n for n in notes)


def test_internal_demand_12_floor_required():
    """Жилой 12 этажей — требуется 1 струя × 2.6 л/с по табл.1."""
    inputs = FireScenarioInput(
        occupancy="residential",
        floors=12,
        volume_m3=15_000,
    )
    q, notes = calc_internal_demand(inputs)
    assert q == pytest.approx(2.6, abs=0.1)


def test_internal_demand_25_floor_three_jets():
    """Жилой 25+ этажей — 3 струи × 2.6 л/с = 7.8 л/с."""
    inputs = FireScenarioInput(
        occupancy="residential",
        floors=25,
        volume_m3=50_000,
    )
    q, notes = calc_internal_demand(inputs)
    assert q == pytest.approx(7.8, abs=0.1)


def test_internal_demand_user_override():
    """Если пользователь явно задал n_jets и расход — берём их."""
    inputs = FireScenarioInput(
        occupancy="public",
        floors=3,  # обычно не требуется
        volume_m3=2000,
        has_internal_system=True,
        n_jets_internal=4,
        jet_flow_lps=5.0,
    )
    q, notes = calc_internal_demand(inputs)
    assert q == pytest.approx(20.0, abs=0.01)


# ──────────────────────────────────────────────────────────────────────────
# Тесты резервуара
# ──────────────────────────────────────────────────────────────────────────


def test_reservoir_volume_basic():
    """V_НЗ = (Q_внешн+Q_внутр)·3.6·T·n
    public V=10000 floors=8 → Q_наруж=15 л/с (табл.1), Q_внутр=2×2.6=5.2 л/с (табл.1 общ. 6-12 эт.)
    Q_total=20.2, T=3 → 20.2·3.6·3 = 218.16 м³ → округление до 250 м³.
    """
    inputs = FireScenarioInput(
        occupancy="public",
        volume_m3=10_000,
        floors=8,
        water_source="reservoir",
        fire_duration_h=3.0,
        n_fires_simultaneous=1,
    )
    result = calculate_fire_scenario(inputs)
    assert result.reservoir is not None
    # 20.2 · 3.6 · 3 ≈ 218 → округляется до стандартного 250
    assert result.reservoir.required_volume_m3 >= 218.0
    assert result.reservoir.required_volume_m3 == 250.0


def test_reservoir_two_tanks_when_large():
    """Если V_НЗ ≥ 1000 → минимум 2 резервуара (СП 8.13130 §9.7)."""
    inputs = FireScenarioInput(
        occupancy="industrial_a",
        volume_m3=300_000,
        water_source="reservoir",
        fire_duration_h=3.0,
        n_fires_simultaneous=2,
    )
    result = calculate_fire_scenario(inputs)
    assert result.reservoir is not None
    assert result.reservoir.required_volume_m3 >= 1000
    assert result.reservoir.n_reservoirs >= 2


# ──────────────────────────────────────────────────────────────────────────
# Тесты насосной станции
# ──────────────────────────────────────────────────────────────────────────


def test_pump_station_has_standby():
    """Резерв ≥1 насос всегда (СП 10.13130 §6.2)."""
    inputs = FireScenarioInput(
        occupancy="residential",
        floors=12,
        volume_m3=20_000,
    )
    result = calculate_fire_scenario(inputs)
    assert result.pump_station.standby_pumps >= 1


def test_pump_station_reliability_category_industrial_a_is_1():
    """Категории А — I кат. надёжности (АВР)."""
    inputs = FireScenarioInput(
        occupancy="industrial_a",
        volume_m3=10_000,
    )
    result = calculate_fire_scenario(inputs)
    assert result.pump_station.reliability_category == 1


def test_pump_station_split_into_two_when_q_high():
    """При Q > 50 л/с — рабочих насосов 2."""
    inputs = FireScenarioInput(
        occupancy="industrial_a",
        volume_m3=400_000,  # Q_наруж = 40
        floors=3,
        # Дополнительно внутренние А кат. дают 8 струй × 5 л/с = 40 л/с
        # суммарно >50
    )
    result = calculate_fire_scenario(inputs)
    if result.demand.total_lps > 50:
        assert result.pump_station.operating_pumps >= 2


# ──────────────────────────────────────────────────────────────────────────
# Полный сценарий
# ──────────────────────────────────────────────────────────────────────────


def test_full_scenario_returns_references():
    """Каждый ответ имеет ссылки на нормативы (для энциклопедии)."""
    inputs = FireScenarioInput(occupancy="residential", floors=12, volume_m3=15_000)
    result = calculate_fire_scenario(inputs)
    assert len(result.references) >= 4
    codes = {r.regulation_code for r in result.references}
    assert any("СП 8.13130" in c for c in codes)
    assert any("СП 10.13130" in c for c in codes)
    assert any("123-ФЗ" in c for c in codes)


def test_full_scenario_jk_50_apartments():
    """Эталонный кейс: ЖК 12 эт., 50 квартир, V=15000 м³.
    Ожидаемые ориентиры:
    - Q_наруж = 15 л/с (V≤25000, табл.1 жилые)
    - Q_внутр = 2.6 л/с (12 этажей)
    - V_резервуара ≈ (15+2.6)·3.6·3 = 190 → округлено до 200 м³
    """
    inputs = FireScenarioInput(
        occupancy="residential",
        floors=12,
        volume_m3=15_000,
        population=150,
        water_source="reservoir",
    )
    result = calculate_fire_scenario(inputs)
    assert result.demand.external_lps == pytest.approx(15.0, abs=0.5)
    assert result.demand.internal_lps == pytest.approx(2.6, abs=0.5)
    assert result.demand.total_lps == pytest.approx(17.6, abs=0.5)
    assert result.reservoir is not None
    # 17.6 · 3.6 · 3 = 190.08 → должно быть ≥190, округление 200
    assert 190 <= result.reservoir.required_volume_m3 <= 250


def test_city_network_warning():
    """При источнике city_network — должно быть предупреждение про акт водоотдачи."""
    inputs = FireScenarioInput(
        occupancy="residential",
        floors=5,
        volume_m3=3000,
        water_source="city_network",
    )
    result = calculate_fire_scenario(inputs)
    assert any("Водоканал" in w or "водоотдач" in w for w in result.warnings)
    assert result.reservoir is None
